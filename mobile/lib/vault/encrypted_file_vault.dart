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


/// A locally stored encrypted file that authenticated successfully but is not
/// safely represented by the current vault index.
class VaultOrphanCandidate {
  const VaultOrphanCandidate({
    required this.id,
    required this.sizeBytes,
    required this.createdAt,
    required this.indexWasCorrupt,
  });

  final String id;
  final int sizeBytes;
  final DateTime createdAt;
  final bool indexWasCorrupt;
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
  // Base64 adds roughly one third to the payload. Leave a small allowance for
  // the JSON envelope while bounding reads of corrupted or tampered files.
  static const int maxVaultEnvelopeBytes = 70 * 1024 * 1024;
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

  /// Reads a file stream while enforcing the beta size limit before buffering
  /// or encrypting the complete payload. A declared size is only an early
  /// rejection hint; the actual stream length is always enforced as well.
  Future<VaultEntry> protectStream({
    required String originalName,
    required Stream<List<int>> chunks,
    int? expectedSize,
  }) async {
    if (expectedSize != null && expectedSize > maxFileBytes) {
      throw ArgumentError('Files must be 50 MB or smaller in this beta.');
    }

    final builder = BytesBuilder(copy: false);
    var totalBytes = 0;
    await for (final chunk in chunks) {
      if (chunk.isEmpty) continue;
      totalBytes += chunk.length;
      if (totalBytes > maxFileBytes) {
        throw ArgumentError('Files must be 50 MB or smaller in this beta.');
      }
      builder.add(chunk);
    }
    if (totalBytes == 0) {
      throw ArgumentError('The selected file is empty.');
    }

    return protectBytes(originalName: originalName, bytes: builder.takeBytes());
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
    final temporaryFile = File('${directory.path}/$id.nsvault.tmp');

    // Write to a temporary file first so a failed write cannot leave a
    // truncated file that looks like a completed vault entry.
    try {
      await temporaryFile.writeAsString(envelope, flush: true);
      await temporaryFile.rename(encryptedFile.path);

      final existing = await listEntries();
      final preferences = await SharedPreferences.getInstance();
      final updated = [...existing, entry];
      final saved = await preferences.setString(
        _indexKey,
        jsonEncode(updated.map((item) => item.toJson()).toList()),
      );
      if (!saved) throw StateError('Could not save the vault index.');
    } catch (_) {
      // Clean up both paths. Cleanup is best-effort so it never masks the
      // original write/index error that caused this operation to fail.
      for (final file in [temporaryFile, encryptedFile]) {
        try {
          if (await file.exists()) await file.delete();
        } catch (_) {
          // Keep the original exception; a later vault audit can detect residue.
        }
      }
      rethrow;
    }
    return entry;
  }

  Future<Uint8List> decryptEntry(String id) async {
    if (!_isValidId(id)) {
      throw ArgumentError.value(id, 'id', 'Invalid vault entry identifier.');
    }
    final entries = await listEntries();
    if (!entries.any((entry) => entry.id == id)) {
      throw StateError('That file is not listed in the vault.');
    }
    return _decryptFile(id);
  }

  /// Finds encrypted files that are not represented by a readable index.
  ///
  /// Every candidate is authenticated with the existing device key before it
  /// is returned. If the index is corrupt, all valid encrypted files are
  /// surfaced for explicit customer review because the damaged index cannot
  /// safely tell us which files were previously registered.
  Future<List<VaultOrphanCandidate>> findRecoverableFiles() async {
    final encodedKey = await _keyStore.readKey();
    if (encodedKey == null) {
      throw StateError('The vault key is missing. Recovery is not possible without it.');
    }
    final keyBytes = base64Decode(encodedKey);
    if (keyBytes.length != 32) throw StateError('The vault key is invalid.');

    var indexWasCorrupt = false;
    var indexedIds = <String>{};
    try {
      indexedIds = (await listEntries()).map((entry) => entry.id).toSet();
    } on StateError {
      indexWasCorrupt = true;
    }

    final directory = await _vaultDirectory();
    if (!await directory.exists()) return const [];
    final candidates = <VaultOrphanCandidate>[];
    await for (final entity in directory.list(followLinks: false)) {
      if (entity is! File) continue;
      final match = RegExp(r'^([a-f0-9]{32})\.nsvault$')
          .firstMatch(entity.uri.pathSegments.last);
      if (match == null) continue;
      final id = match.group(1)!;
      if (!indexWasCorrupt && indexedIds.contains(id)) continue;
      try {
        final clear = await _decryptFile(id);
        candidates.add(VaultOrphanCandidate(
          id: id,
          sizeBytes: clear.length,
          createdAt: await entity.lastModified(),
          indexWasCorrupt: indexWasCorrupt,
        ));
      } catch (_) {
        // Invalid, truncated or unauthenticated files are never offered for
        // recovery. They remain untouched for later forensic inspection.
      }
    }
    candidates.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return List.unmodifiable(candidates);
  }

  /// Authenticates and registers one customer-selected orphan without changing
  /// its encrypted file. A corrupt index is preserved under a separate
  /// timestamped preference key before a new index is written.
  Future<VaultEntry> recoverOrphanedEntry({
    required String id,
    required String recoveredName,
  }) async {
    if (!_isValidId(id)) {
      throw ArgumentError.value(id, 'id', 'Invalid vault entry identifier.');
    }

    var existingEntries = <VaultEntry>[];
    var indexWasCorrupt = false;
    try {
      existingEntries = await listEntries();
    } on StateError {
      indexWasCorrupt = true;
    }
    if (existingEntries.any((entry) => entry.id == id)) {
      throw StateError('That file is already listed in the vault.');
    }

    final safeName = _safeName(recoveredName);
    if (safeName.isEmpty) {
      throw ArgumentError.value(recoveredName, 'recoveredName', 'A filename is required.');
    }

    // Do not write any index metadata until the existing key has authenticated
    // the exact encrypted file selected by the customer.
    final clear = await _decryptFile(id);
    final directory = await _vaultDirectory();
    final file = File('${directory.path}/$id.nsvault');
    final entry = VaultEntry(
      id: id,
      name: safeName,
      sizeBytes: clear.length,
      createdAt: await file.lastModified(),
    );

    final preferences = await SharedPreferences.getInstance();
    if (indexWasCorrupt) {
      final damagedIndex = preferences.getString(_indexKey);
      if (damagedIndex != null) {
        final backupKey =
            'neon_shield.encrypted_vault_corrupt_index_backup_${DateTime.now().microsecondsSinceEpoch}';
        final backedUp = await preferences.setString(backupKey, damagedIndex);
        if (!backedUp) {
          throw StateError('The damaged vault index could not be preserved. Recovery was not applied.');
        }
      }
    }

    final updated = [...existingEntries, entry];
    final saved = await preferences.setString(
      _indexKey,
      jsonEncode(updated.map((item) => item.toJson()).toList()),
    );
    if (!saved) throw StateError('The vault index could not be updated.');
    return entry;
  }

  bool _isValidId(String id) => RegExp(r'^[a-f0-9]{32}$').hasMatch(id);

  Future<Uint8List> _decryptFile(String id) async {
    final encodedKey = await _keyStore.readKey();
    if (encodedKey == null) {
      throw StateError('The vault key is missing. Recovery is not possible without it.');
    }
    final keyBytes = base64Decode(encodedKey);
    if (keyBytes.length != 32) throw StateError('The vault key is invalid.');

    final directory = await _vaultDirectory();
    final file = File('${directory.path}/$id.nsvault');
    if (!await file.exists()) throw StateError('The encrypted file is missing.');
    if (await file.length() > maxVaultEnvelopeBytes) {
      throw const FormatException('Encrypted file exceeds the supported vault size.');
    }

    final decoded = jsonDecode(await file.readAsString());
    if (decoded is! Map<String, dynamic> || decoded['version'] != 1) {
      throw const FormatException('Unsupported encrypted-file format.');
    }
    final nonceValue = decoded['nonce'];
    final macValue = decoded['mac'];
    final ciphertextValue = decoded['ciphertext'];
    if (nonceValue is! String ||
        macValue is! String ||
        ciphertextValue is! String) {
      throw const FormatException('Encrypted-file envelope is incomplete.');
    }

    final nonce = base64Decode(nonceValue);
    final mac = base64Decode(macValue);
    final ciphertext = base64Decode(ciphertextValue);
    if (nonce.length != 12 ||
        mac.length != 16 ||
        ciphertext.isEmpty ||
        ciphertext.length > maxFileBytes) {
      throw const FormatException('Encrypted-file envelope has invalid lengths.');
    }

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
    if (!entries.any((entry) => entry.id == id)) {
      throw StateError('That file is not listed in the vault.');
    }
    final directory = await _vaultDirectory();
    final file = File('${directory.path}/$id.nsvault');
    final preferences = await SharedPreferences.getInstance();
    final updated = entries.where((entry) => entry.id != id).toList();
    final previousIndex = jsonEncode(entries.map((entry) => entry.toJson()).toList());
    final updatedIndex = jsonEncode(updated.map((entry) => entry.toJson()).toList());
    final saved = await preferences.setString(_indexKey, updatedIndex);
    if (!saved) throw StateError('The vault index could not be updated.');
    try {
      if (await file.exists()) await file.delete();
    } catch (_) {
      // Restore the visible entry if deleting the encrypted file failed.
      await preferences.setString(_indexKey, previousIndex);
      rethrow;
    }
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

    // A crash can occur after the encrypted file is renamed into place but
    // before the index is saved. Never generate a replacement key while
    // encrypted files or temporary write remnants may still need the old key.
    final directory = await _vaultDirectory();
    final hasVaultResidue = await directory
        .list()
        .any((entity) =>
            entity is File &&
            (entity.path.endsWith('.nsvault') ||
                entity.path.endsWith('.nsvault.tmp')));
    if (hasVaultResidue) {
      throw StateError(
        'The vault key is missing while encrypted vault files remain. '
        'Refusing to create a replacement key to protect recoverability.',
      );
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
)
          .firstMatch(entity.uri.pathSegments.last);
      if (match == null) continue;
      final id = match.group(1)!;
      if (!indexWasCorrupt && indexedIds.contains(id)) continue;
      try {
        final clear = await _decryptFile(id);
        candidates.add(VaultOrphanCandidate(
          id: id,
          sizeBytes: clear.length,
          createdAt: await entity.lastModified(),
          indexWasCorrupt: indexWasCorrupt,
        ));
      } catch (_) {
        // Invalid, truncated or unauthenticated files are never offered for
        // recovery. They remain untouched for later forensic inspection.
      }
    }
    candidates.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return List.unmodifiable(candidates);
  }

  /// Authenticates and registers one customer-selected orphan without changing
  /// its encrypted file. A corrupt index is preserved under a separate
  /// timestamped preference key before a new index is written.
  Future<VaultEntry> recoverOrphanedEntry({
    required String id,
    required String recoveredName,
  }) async {
    if (!_isValidId(id)) {
      throw ArgumentError.value(id, 'id', 'Invalid vault entry identifier.');
    }

    var existingEntries = <VaultEntry>[];
    var indexWasCorrupt = false;
    try {
      existingEntries = await listEntries();
    } on StateError {
      indexWasCorrupt = true;
    }
    if (existingEntries.any((entry) => entry.id == id)) {
      throw StateError('That file is already listed in the vault.');
    }

    final safeName = _safeName(recoveredName);
    if (safeName.isEmpty) {
      throw ArgumentError.value(recoveredName, 'recoveredName', 'A filename is required.');
    }

    // Do not write any index metadata until the existing key has authenticated
    // the exact encrypted file selected by the customer.
    final clear = await _decryptFile(id);
    final directory = await _vaultDirectory();
    final file = File('${directory.path}/$id.nsvault');
    final entry = VaultEntry(
      id: id,
      name: safeName,
      sizeBytes: clear.length,
      createdAt: await file.lastModified(),
    );

    final preferences = await SharedPreferences.getInstance();
    if (indexWasCorrupt) {
      final damagedIndex = preferences.getString(_indexKey);
      if (damagedIndex != null) {
        final backupKey =
            'neon_shield.encrypted_vault_corrupt_index_backup_${DateTime.now().microsecondsSinceEpoch}';
        final backedUp = await preferences.setString(backupKey, damagedIndex);
        if (!backedUp) {
          throw StateError('The damaged vault index could not be preserved. Recovery was not applied.');
        }
      }
    }

    final updated = [...existingEntries, entry];
    final saved = await preferences.setString(
      _indexKey,
      jsonEncode(updated.map((item) => item.toJson()).toList()),
    );
    if (!saved) throw StateError('The vault index could not be updated.');
    return entry;
  }

  bool _isValidId(String id) => RegExp(r'^[a-f0-9]{32}$').hasMatch(id);

  Future<Uint8List> _decryptFile(String id) async {
    final encodedKey = await _keyStore.readKey();
    if (encodedKey == null) {
      throw StateError('The vault key is missing. Recovery is not possible without it.');
    }
    final keyBytes = base64Decode(encodedKey);
    if (keyBytes.length != 32) throw StateError('The vault key is invalid.');

    final directory = await _vaultDirectory();
    final file = File('${directory.path}/$id.nsvault');
    if (!await file.exists()) throw StateError('The encrypted file is missing.');
    if (await file.length() > maxVaultEnvelopeBytes) {
      throw const FormatException('Encrypted file exceeds the supported vault size.');
    }

    final decoded = jsonDecode(await file.readAsString());
    if (decoded is! Map<String, dynamic> || decoded['version'] != 1) {
      throw const FormatException('Unsupported encrypted-file format.');
    }
    final nonceValue = decoded['nonce'];
    final macValue = decoded['mac'];
    final ciphertextValue = decoded['ciphertext'];
    if (nonceValue is! String ||
        macValue is! String ||
        ciphertextValue is! String) {
      throw const FormatException('Encrypted-file envelope is incomplete.');
    }

    final nonce = base64Decode(nonceValue);
    final mac = base64Decode(macValue);
    final ciphertext = base64Decode(ciphertextValue);
    if (nonce.length != 12 ||
        mac.length != 16 ||
        ciphertext.isEmpty ||
        ciphertext.length > maxFileBytes) {
      throw const FormatException('Encrypted-file envelope has invalid lengths.');
    }

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
    if (!entries.any((entry) => entry.id == id)) {
      throw StateError('That file is not listed in the vault.');
    }
    final directory = await _vaultDirectory();
    final file = File('${directory.path}/$id.nsvault');
    final preferences = await SharedPreferences.getInstance();
    final updated = entries.where((entry) => entry.id != id).toList();
    final previousIndex = jsonEncode(entries.map((entry) => entry.toJson()).toList());
    final updatedIndex = jsonEncode(updated.map((entry) => entry.toJson()).toList());
    final saved = await preferences.setString(_indexKey, updatedIndex);
    if (!saved) throw StateError('The vault index could not be updated.');
    try {
      if (await file.exists()) await file.delete();
    } catch (_) {
      // Restore the visible entry if deleting the encrypted file failed.
      await preferences.setString(_indexKey, previousIndex);
      rethrow;
    }
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

    // A crash can occur after the encrypted file is renamed into place but
    // before the index is saved. Never generate a replacement key while
    // encrypted files or temporary write remnants may still need the old key.
    final directory = await _vaultDirectory();
    final hasVaultResidue = await directory
        .list()
        .any((entity) =>
            entity is File &&
            (entity.path.endsWith('.nsvault') ||
                entity.path.endsWith('.nsvault.tmp')));
    if (hasVaultResidue) {
      throw StateError(
        'The vault key is missing while encrypted vault files remain. '
        'Refusing to create a replacement key to protect recoverability.',
      );
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
