import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:illumyx_neon_shield/vault/encrypted_file_vault.dart';

class _MemoryVaultKeyStore implements VaultKeyStore {
  String? key;

  @override
  Future<String?> readKey() async => key;

  @override
  Future<void> writeKey(String encodedKey) async {
    key = encodedKey;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Directory tempDirectory;
  late _MemoryVaultKeyStore keyStore;
  late EncryptedFileVault vault;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    tempDirectory = await Directory.systemTemp.createTemp('neon-vault-test-');
    keyStore = _MemoryVaultKeyStore();
    vault = EncryptedFileVault(
      keyStore: keyStore,
      directoryProvider: () async => tempDirectory,
    );
  });

  tearDown(() async {
    if (await tempDirectory.exists()) {
      await tempDirectory.delete(recursive: true);
    }
  });

  test('encrypts a file copy and decrypts it byte-for-byte', () async {
    final clear = utf8.encode('private ILLUMYX project document');

    final entry = await vault.protectBytes(
      originalName: '../private-project.txt',
      bytes: clear,
    );

    expect(entry.name, 'private-project.txt');
    expect(keyStore.key, isNotNull);
    final encryptedFile = File('${tempDirectory.path}/neon_shield_vault/${entry.id}.nsvault');
    expect(await encryptedFile.exists(), isTrue);
    expect(await encryptedFile.readAsString(), isNot(contains('private ILLUMYX project document')));
    expect(await vault.listEntries(), hasLength(1));
    expect(await vault.decryptEntry(entry.id), clear);
  });

  test('rejects ciphertext tampering through authenticated decryption', () async {
    final entry = await vault.protectBytes(
      originalName: 'integrity.txt',
      bytes: utf8.encode('authenticated content'),
    );
    final encryptedFile = File('${tempDirectory.path}/neon_shield_vault/${entry.id}.nsvault');
    final envelope = jsonDecode(await encryptedFile.readAsString()) as Map<String, dynamic>;
    final ciphertext = envelope['ciphertext'] as String;
    envelope['ciphertext'] = '${ciphertext.startsWith('A') ? 'B' : 'A'}${ciphertext.substring(1)}';
    await encryptedFile.writeAsString(jsonEncode(envelope), flush: true);

    await expectLater(vault.decryptEntry(entry.id), throwsA(anything));
  });

  test('rejects malformed envelope fields before decryption', () async {
    final entry = await vault.protectBytes(
      originalName: 'malformed-envelope.txt',
      bytes: utf8.encode('protected content'),
    );
    final encryptedFile =
        File('${tempDirectory.path}/neon_shield_vault/${entry.id}.nsvault');
    final envelope =
        jsonDecode(await encryptedFile.readAsString()) as Map<String, dynamic>;
    envelope['nonce'] = 42;
    await encryptedFile.writeAsString(jsonEncode(envelope), flush: true);

    await expectLater(
      vault.decryptEntry(entry.id),
      throwsA(isA<FormatException>()),
    );
  });

  test('rejects invalid AES-GCM nonce and authentication-tag lengths', () async {
    final entry = await vault.protectBytes(
      originalName: 'invalid-crypto-lengths.txt',
      bytes: utf8.encode('protected content'),
    );
    final encryptedFile =
        File('${tempDirectory.path}/neon_shield_vault/${entry.id}.nsvault');
    final envelope =
        jsonDecode(await encryptedFile.readAsString()) as Map<String, dynamic>;
    envelope['nonce'] = base64Encode(utf8.encode('too-short'));
    await encryptedFile.writeAsString(jsonEncode(envelope), flush: true);

    await expectLater(
      vault.decryptEntry(entry.id),
      throwsA(isA<FormatException>()),
    );
  });

  test('rejects invalid AES-GCM authentication-tag length', () async {
    final entry = await vault.protectBytes(
      originalName: 'invalid-authentication-tag.txt',
      bytes: utf8.encode('protected content'),
    );
    final encryptedFile =
        File('${tempDirectory.path}/neon_shield_vault/${entry.id}.nsvault');
    final envelope =
        jsonDecode(await encryptedFile.readAsString()) as Map<String, dynamic>;
    envelope['mac'] = base64Encode(utf8.encode('too-short'));
    await encryptedFile.writeAsString(jsonEncode(envelope), flush: true);

    await expectLater(
      vault.decryptEntry(entry.id),
      throwsA(isA<FormatException>()),
    );
  });

  test('rejects empty and oversized files before writing anything', () async {
    await expectLater(
      vault.protectBytes(originalName: 'empty.txt', bytes: const []),
      throwsArgumentError,
    );
    await expectLater(
      vault.protectBytes(
        originalName: 'too-large.bin',
        bytes: List<int>.filled(EncryptedFileVault.maxFileBytes + 1, 1),
      ),
      throwsArgumentError,
    );
    expect(await vault.listEntries(), isEmpty);
  });

  test('rejects oversized declared streams before reading or creating a key', () async {
    var streamListenedTo = false;
    Stream<List<int>> chunks() async* {
      streamListenedTo = true;
      yield [1];
    }

    await expectLater(
      vault.protectStream(
        originalName: 'too-large.bin',
        chunks: chunks(),
        expectedSize: EncryptedFileVault.maxFileBytes + 1,
      ),
      throwsArgumentError,
    );

    expect(streamListenedTo, isFalse);
    expect(keyStore.key, isNull);
    expect(await vault.listEntries(), isEmpty);
  });

  test('rejects an oversized actual stream when declared size is understated', () async {
    Stream<List<int>> oversizedChunks() async* {
      for (var i = 0; i < 51; i++) {
        yield List<int>.filled(1024 * 1024, 7);
      }
    }

    await expectLater(
      vault.protectStream(
        originalName: 'understated-size.bin',
        chunks: oversizedChunks(),
        expectedSize: 1,
      ),
      throwsArgumentError,
    );

    expect(keyStore.key, isNull);
    expect(await vault.listEntries(), isEmpty);
  });

  test('accepts a stream exactly at the configured size limit', () async {
    Stream<List<int>> exactLimitChunks() async* {
      for (var i = 0; i < 50; i++) {
        yield List<int>.filled(1024 * 1024, 7);
      }
    }

    final entry = await vault.protectStream(
      originalName: 'exact-limit.bin',
      chunks: exactLimitChunks(),
      expectedSize: EncryptedFileVault.maxFileBytes,
    );

    expect(entry.sizeBytes, EncryptedFileVault.maxFileBytes);
    expect(keyStore.key, isNotNull);
    expect(await vault.listEntries(), hasLength(1));
  });

  test('a stream failure does not create a key or vault entry', () async {
    Stream<List<int>> failingChunks() async* {
      yield [1, 2, 3];
      throw StateError('simulated read failure');
    }

    await expectLater(
      vault.protectStream(
        originalName: 'read-failure.bin',
        chunks: failingChunks(),
      ),
      throwsA(isA<StateError>()),
    );

    expect(keyStore.key, isNull);
    expect(await vault.listEntries(), isEmpty);
  });

  test('stops an oversized stream at the configured limit', () async {
    var chunksYielded = 0;
    Stream<List<int>> oversizedChunks() async* {
      for (var i = 0; i < 51; i++) {
        chunksYielded++;
        yield List<int>.filled(1024 * 1024, 7);
      }
    }

    await expectLater(
      vault.protectStream(
        originalName: 'stream-too-large.bin',
        chunks: oversizedChunks(),
      ),
      throwsArgumentError,
    );

    expect(chunksYielded, 51);
    expect(keyStore.key, isNull);
    expect(await vault.listEntries(), isEmpty);
  });


  test('recovers a valid orphaned encrypted file without deleting it', () async {
    final original = utf8.encode('recover this encrypted copy safely');
    final created = await vault.protectBytes(
      originalName: 'original-note.txt',
      bytes: original,
    );
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString('neon_shield.encrypted_vault_index_v1', '[]');

    final recovered = await vault.recoverOrphanedEntry(
      id: created.id,
      recoveredName: 'recovered-note.txt',
    );

    expect(recovered.id, created.id);
    expect(recovered.name, 'recovered-note.txt');
    expect(await vault.listEntries(), hasLength(1));
    expect(await vault.decryptEntry(created.id), orderedEquals(original));

    final vaultDirectory = Directory('${tempDirectory.path}/neon_shield_vault');
    expect(await File('${vaultDirectory.path}/${created.id}.nsvault').exists(), isTrue);
  });

  test('discovers and recovers authenticated files when the index is corrupt without deleting data', () async {
    final first = await vault.protectBytes(
      originalName: 'first-original.txt',
      bytes: utf8.encode('first encrypted payload'),
    );
    final second = await vault.protectBytes(
      originalName: 'second-original.txt',
      bytes: utf8.encode('second encrypted payload'),
    );
    const damagedIndex = '{not-valid-vault-index';
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString('neon_shield.encrypted_vault_index_v1', damagedIndex);

    final candidates = await vault.findRecoverableFiles();
    expect(candidates.map((candidate) => candidate.id).toSet(),
        {first.id, second.id});
    expect(candidates.every((candidate) => candidate.indexWasCorrupt), isTrue);

    final recovered = await vault.recoverOrphanedEntry(
      id: first.id,
      recoveredName: 'first-recovered.txt',
    );
    expect(recovered.sizeBytes, utf8.encode('first encrypted payload').length);
    expect(await vault.listEntries(), hasLength(1));

    final backupKeys = preferences.getKeys().where((key) =>
        key.startsWith('neon_shield.encrypted_vault_corrupt_index_backup_'));
    expect(backupKeys, hasLength(1));
    expect(preferences.getString(backupKeys.single), damagedIndex);

    final directory = Directory('${tempDirectory.path}/neon_shield_vault');
    expect(await File('${directory.path}/${first.id}.nsvault').exists(), isTrue);
    expect(await File('${directory.path}/${second.id}.nsvault').exists(), isTrue);
    expect(await vault.decryptEntry(first.id),
        utf8.encode('first encrypted payload'));

    final remaining = await vault.findRecoverableFiles();
    expect(remaining.map((candidate) => candidate.id), [second.id]);
    await vault.recoverOrphanedEntry(
      id: second.id,
      recoveredName: 'second-recovered.txt',
    );
    expect(await vault.listEntries(), hasLength(2));
    expect(await File('${directory.path}/${second.id}.nsvault').exists(), isTrue);
  });

  test('does not offer unauthenticated encrypted files for recovery', () async {
    final entry = await vault.protectBytes(
      originalName: 'tampered-orphan.txt',
      bytes: utf8.encode('authenticated before tampering'),
    );
    final encryptedFile =
        File('${tempDirectory.path}/neon_shield_vault/${entry.id}.nsvault');
    final envelope =
        jsonDecode(await encryptedFile.readAsString()) as Map<String, dynamic>;
    final ciphertext = envelope['ciphertext'] as String;
    envelope['ciphertext'] =
        '${ciphertext.startsWith('A') ? 'B' : 'A'}${ciphertext.substring(1)}';
    await encryptedFile.writeAsString(jsonEncode(envelope), flush: true);
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(
      'neon_shield.encrypted_vault_index_v1',
      'corrupt-index',
    );

    expect(await vault.findRecoverableFiles(), isEmpty);
    expect(await encryptedFile.exists(), isTrue);
    expect(preferences.getString('neon_shield.encrypted_vault_index_v1'),
        'corrupt-index');
  });

  test('does not register an orphan when the encryption key is missing', () async {
    final created = await vault.protectBytes(
      originalName: 'orphan.txt',
      bytes: utf8.encode('keep encrypted data untouched'),
    );
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString('neon_shield.encrypted_vault_index_v1', '[]');
    keyStore.key = null;

    await expectLater(
      vault.recoverOrphanedEntry(
        id: created.id,
        recoveredName: 'recovered.txt',
      ),
      throwsA(isA<StateError>()),
    );
    expect(await vault.listEntries(), isEmpty);
    final vaultDirectory = Directory('${tempDirectory.path}/neon_shield_vault');
    expect(await File('${vaultDirectory.path}/${created.id}.nsvault').exists(), isTrue);
  });

  test('refuses to create a replacement key when orphaned encrypted files remain', () async {
    final vaultDirectory = Directory('${tempDirectory.path}/neon_shield_vault');
    await vaultDirectory.create(recursive: true);
    final orphan = File('${vaultDirectory.path}/orphaned-entry.nsvault');
    await orphan.writeAsString('encrypted payload from an interrupted save');

    await expectLater(
      vault.protectBytes(
        originalName: 'new-file.txt',
        bytes: utf8.encode('must not overwrite recoverability'),
      ),
      throwsA(isA<StateError>()),
    );

    expect(keyStore.key, isNull);
    expect(await orphan.exists(), isTrue);
    expect(await vault.listEntries(), isEmpty);
  });

  test('refuses to silently replace a missing key for existing vault entries', () async {
    final entry = await vault.protectBytes(
      originalName: 'notes.txt',
      bytes: utf8.encode('keep this safe'),
    );
    keyStore.key = null;

    await expectLater(
      vault.protectBytes(originalName: 'another.txt', bytes: utf8.encode('new file')),
      throwsA(isA<StateError>()),
    );
    await expectLater(
      vault.decryptEntry(entry.id),
      throwsA(isA<StateError>()),
    );
    expect(await vault.listEntries(), hasLength(1));
  });

  test('removes only the encrypted copy and updates the index', () async {
    final entry = await vault.protectBytes(
      originalName: 'keep-original.txt',
      bytes: utf8.encode('original remains outside this vault'),
    );
    final encryptedFile = File('${tempDirectory.path}/neon_shield_vault/${entry.id}.nsvault');

    await vault.removeEncryptedCopy(entry.id);

    expect(await encryptedFile.exists(), isFalse);
    expect(await vault.listEntries(), isEmpty);
  });

  test('cleans up encrypted and temporary files when index update fails', () async {
    // A valid existing key lets encryption proceed, while a corrupt index
    // forces the post-write index read to fail and exercises rollback cleanup.
    keyStore.key = base64Encode(List<int>.filled(32, 1));
    SharedPreferences.setMockInitialValues({
      'neon_shield.encrypted_vault_index_v1': 'not-valid-json',
    });

    await expectLater(
      vault.protectBytes(
        originalName: 'index-failure.txt',
        bytes: utf8.encode('must not leave an orphaned encrypted file'),
      ),
      throwsA(isA<StateError>()),
    );

    final vaultDirectory = Directory('${tempDirectory.path}/neon_shield_vault');
    final remainingFiles = await vaultDirectory.list().toList();
    expect(
      remainingFiles.where(
        (file) => file.path.endsWith('.nsvault') || file.path.endsWith('.nsvault.tmp'),
      ),
      isEmpty,
    );
  });

  test('rejects unknown entry identifiers', () async {
    await expectLater(
      vault.decryptEntry('not-a-vault-id'),
      throwsArgumentError,
    );
  });
}
