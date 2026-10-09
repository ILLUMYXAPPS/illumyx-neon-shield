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

  test('rejects unknown entry identifiers', () async {
    await expectLater(
      vault.decryptEntry('not-a-vault-id'),
      throwsArgumentError,
    );
  });
}
