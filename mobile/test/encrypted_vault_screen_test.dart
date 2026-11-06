import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:illumyx_neon_shield/vault/encrypted_file_vault.dart';
import 'package:illumyx_neon_shield/vault/encrypted_vault_screen.dart';

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

  testWidgets(
    'customer can review and confirm an authenticated file when the index is corrupt',
    (tester) async {
      SharedPreferences.setMockInitialValues({});
      final directory = await Directory.systemTemp.createTemp('neon-vault-screen-');
      final keyStore = _MemoryVaultKeyStore();
      final vault = EncryptedFileVault(
        keyStore: keyStore,
        directoryProvider: () async => directory,
      );

      try {
        final created = await vault.protectBytes(
          originalName: 'original-name-is-not-in-envelope.txt',
          bytes: utf8.encode('recover through the customer flow'),
        );
        final preferences = await SharedPreferences.getInstance();
        await preferences.setString(
          'neon_shield.encrypted_vault_index_v1',
          'damaged-index-content',
        );

        await tester.pumpWidget(
          MaterialApp(home: EncryptedVaultScreen(vault: vault)),
        );
        await tester.pumpAndSettle();

        expect(find.textContaining('vault index could not be read'), findsOneWidget);
        expect(find.text('Verified encrypted file'), findsOneWidget);
        expect(find.text('Review'), findsOneWidget);

        await tester.tap(find.text('Review'));
        // The review dialog autofocuses its TextField. Its blinking cursor is
        // an ongoing animation, so pumpAndSettle would wait forever here.
        // Pump the route transition once, then interact with the field.
        await tester.pump();
        await tester.enterText(find.byType(TextField), 'customer-recovered.txt');
        await tester.tap(find.text('Recover listing'));
        // The previously focused review TextField can leave a cursor animation
        // active during the route transition. Pump the dialog transition without
        // waiting for every animation in the test binding to become idle.
        await tester.pump();

        expect(find.text('Confirm vault recovery'), findsOneWidget);
        await tester.tap(find.text('Confirm recovery'));
        // The recovery callback performs real filesystem and preference I/O.
        // Let those platform futures run outside the widget test's fake clock,
        // then pump the resulting UI updates. A bounded wait avoids both
        // deadlocking file I/O and waiting forever on repeating animations.
        await tester.runAsync(() async {
          await Future<void>.delayed(const Duration(milliseconds: 250));
        });
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        await tester.pump();

        final entries = await vault.listEntries();
        expect(entries, hasLength(1));
        expect(entries.single.id, created.id);
        expect(entries.single.name, 'customer-recovered.txt');
        expect(
          await File('${directory.path}/neon_shield_vault/${created.id}.nsvault').exists(),
          isTrue,
        );
        expect(
          preferences.getKeys().where((key) => key.startsWith(
              'neon_shield.encrypted_vault_corrupt_index_backup_')),
          hasLength(1),
        );
      } finally {
        if (await directory.exists()) {
          await directory.delete(recursive: true);
        }
      }
    },
  );
}
