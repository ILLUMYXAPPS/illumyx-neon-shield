import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

abstract interface class VaultKeyStore {
  Future<String?> readKey();
  Future<void> writeKey(String encodedKey);
}

class SecureVaultKeyStore implements VaultKeyStore {
  SecureVaultKeyStore({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  static const _keyName = 'neon_shield.vault_key_v1';
  final FlutterSecureStorage _storage;

  @override
  Future<String?> readKey() => _storage.read(key: _keyName);

  @override
  Future<void> writeKey(String encodedKey) =>
      _storage.write(key: _keyName, value: encodedKey);
}

class VaultEntry {
  const VaultEntry({
    required this.id,
    required this.name,
    required this.sizeBytes,
    required this.createdAt,
  });

  final String id;
  final String name;
  final int sizeBytes;
  final DateTime createdAt;

  Map<String, Object> toJson() => {
        'id': id,
        'name': name,
        'sizeBytes': sizeBytes,
        'createdAt': createdAt.toUtc().toIso8601String(),
      };

  factory VaultEntry.fromJson(Map<String, dynamic> json) {
    final id = json['id'];
    final name = json['name'];
    final size = json['sizeBytes'];
    final created = json['createdAt'];
    if (id is! String ||
        !RegExp(r'^[a-f0-9]{32}$').hasMatch(id) ||
        name is! String ||
        name.isEmpty ||
        size is! int ||
        size < 0 ||
        created is! String) {
      throw const FormatException('Invalid encrypted-vault metadata.');
    }
    return VaultEntry(
      id: id,
      name: name,
      sizeBytes: size,
      createdAt: DateTime.parse(created).toUtc(),
    );
  }
}

/// Encrypted copy vault. It never deletes or modifies the user's original file.
/// The AES-256-GCM key is stored separately in platform secure storage.
class EncryptedFileVault {
  EncryptedFileVault({
    VaultKeyStore? keyStore,
    Future<Directory> Function()? directoryProvider,
  })  : _keyStore = keyStore ?? SecureVaultKeyStore(),
        _directoryProvider =
            directoryProvider ?? getApplicationDocumentsDirectory;

  static const int maxFileBytes = 50 * 1024 * 1024;
  static const _indexKey = 'neon_shield.encrypted_vault_index_v1';
  static final _cipher = AesGcm.with256bits();

  final VaultKeyStore _keyStore;
  final Future<Directory> Function() _directoryProvider;
  final Random _random = Random.secure();

  Future<List<VaultEntry>> listEntries() async {
    final preferences = await SharedPreferences.getInstance();
    final raw = preferences.getString(_indexKey);
    if (raw == null || raw.isEmpty) return const [];
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! List) throw const FormatException();
      final entries = decoded
          .map((item) {
            if (item is! Map<String, dynamic>) {
              throw const FormatException();
            }
            return VaultEntry.fromJson(item);
          })
          .toList()
        ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
      return List.unmodifiable(entries);
    } on FormatException {
      throw StateError('Vault index is unreadable. Encrypted files were not changed.');
    }
  }

  Future<VaultEntry> protectBytes({
    required String originalName,
    required List<int> bytes,
  }) async {
    if (bytes.isEmpty) throw ArgumentError('The selected file is empty.');
    if (bytes.length > maxFileBytes) {
      throw ArgumentError('Files must be 50 MB or smaller in this beta.');
    }
    final safeName = _safeName(originalName);
    final key = await _loadOrCreateKey();
    final nonce = _cipher.newNonce();
    final secretBox = await _cipher.encrypt(
      bytes,
      secretKey: key,
      nonce: nonce,
    );
    final envelope = jsonEncode({
      'version': 1,
      'nonce': base64Encode(secretBox.nonce),
      'mac': base64Encode(secretBox.mac.bytes),
      'ciphertext': base64Encode(secretBox.cipherText),
    });

    final id = List<int>.generate(16, (_) => _random.nextInt(256))
        .map((value) => value.toRadixString(16).padLeft(2, '0'))
        .join();
    final entry = VaultEntry(
      id: id,
      name: safeName,
      sizeBytes: bytes.length,
      createdAt: DateTime.now().toUtc(),
    );
    final directory = await _vaultDirectory();
    final encryptedFile = File('${directory.path}/$id.nsvault');
    await encryptedFile.writeAsString(envelope, flush: true);
    try {
      final existing = await listEntries();
      final preferences = await SharedPreferences.getInstance();
      final updated = [...existing, entry];
      final saved = await preferences.setString(
        _indexKey,
        jsonEncode(updated.map((item) => item.toJson()).toList()),
      );
      if (!saved) throw StateError('Could not save the vault index.');
    } catch (_) {
      if (await encryptedFile.exists()) await encryptedFile.delete();
      rethrow;
    }
    return entry;
  }

  Future<Uint8List> decryptEntry(String id) async {
    if (!RegExp(r'^[a-f0-9]{32}$').hasMatch(id)) {
      throw ArgumentError.value(id, 'id', 'Invalid vault entry identifier.');
    }
    final entries = await listEntries();
    if (!entries.any((entry) => entry.id == id)) {
      throw StateError('That file is not listed in the vault.');
    }
    final encodedKey = await _keyStore.readKey();
    if (encodedKey == null) {
      throw StateError('The vault key is missing. Recovery is not possible without it.');
    }
    final keyBytes = base64Decode(encodedKey);
    if (keyBytes.length != 32) throw StateError('The vault key is invalid.');
    final directory = await _vaultDirectory();
    final file = File('${directory.path}/$id.nsvault');
    if (!await file.exists()) throw StateError('The encrypted file is missing.');
    final decoded = jsonDecode(await file.readAsString());
    if (decoded is! Map<String, dynamic> || decoded['version'] != 1) {
      throw const FormatException('Unsupported encrypted-file format.');
    }
    final nonce = base64Decode(decoded['nonce'] as String);
    final mac = base64Decode(decoded['mac'] as String);
    final ciphertext = base64Decode(decoded['ciphertext'] as String);
    final clear = await _cipher.decrypt(
      SecretBox(ciphertext, nonce: nonce, mac: Mac(mac)),
      secretKey: SecretKey(keyBytes),
    );
    return Uint8List.fromList(clear);
  }

  Future<void> removeEncryptedCopy(String id) async {
    if (!RegExp(r'^[a-f0-9]{32}$').hasMatch(id)) {
      throw ArgumentError.value(id, 'id', 'Invalid vault entry identifier.');
    }
    final entries = await listEntries();
    final target = entries.where((entry) => entry.id == id).firstOrNull;
    if (target == null) throw StateError('That file is not listed in the vault.');
    final directory = await _vaultDirectory();
    final file = File('${directory.path}/$id.nsvault');
    if (await file.exists()) await file.delete();
    final preferences = await SharedPreferences.getInstance();
    final updated = entries.where((entry) => entry.id != id).toList();
    final saved = await preferences.setString(
      _indexKey,
      jsonEncode(updated.map((entry) => entry.toJson()).toList()),
    );
    if (!saved) throw StateError('The vault index could not be updated.');
  }

  Future<SecretKey> _loadOrCreateKey() async {
    final stored = await _keyStore.readKey();
    if (stored != null) {
      final bytes = base64Decode(stored);
      if (bytes.length != 32) throw StateError('The vault key is invalid.');
      return SecretKey(bytes);
    }
    if ((await listEntries()).isNotEmpty) {
      throw StateError('The vault key is missing. Refusing to replace it because existing files would become unrecoverable.');
    }
    final key = await _cipher.newSecretKey();
    await _keyStore.writeKey(base64Encode(await key.extractBytes()));
    return key;
  }

  Future<Directory> _vaultDirectory() async {
    final root = await _directoryProvider();
    final directory = Directory('${root.path}/neon_shield_vault');
    if (!await directory.exists()) await directory.create(recursive: true);
    return directory;
  }

  String _safeName(String name) {
    final leaf = name.replaceAll('\\', '/').split('/').last.trim();
    final cleaned = leaf.replaceAll(RegExp(r'[^a-zA-Z0-9._ ()-]'), '_');
    if (cleaned.isEmpty || cleaned == '.' || cleaned == '..') {
      throw ArgumentError('The selected filename is invalid.');
    }
    return cleaned.length > 180 ? cleaned.substring(0, 180) : cleaned;
  }
}
