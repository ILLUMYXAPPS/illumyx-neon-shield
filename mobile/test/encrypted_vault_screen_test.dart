import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:illumyx_neon_shield/vault/encrypted_file_vault.dart';
import 'package:illumyx_neon_shield/vault/encrypted_vault_screen.dart';

class _MemoryVaultKeyStore implements VaultKeyStore {
  @override
  Future<String?> readKey() async => null;

  @override
  Future<void> writeKey(String encodedKey) async {}
}

/// Keeps this widget test focused on the customer confirmation flow.
/// The real encryption, authentication, index backup and filesystem behavior
/// are covered by EncryptedFileVault unit tests.
class _RecoveryFlowVault extends EncryptedFileVault {
  _RecoveryFlowVault() : super(keyStore: _MemoryVaultKeyStore());

  static const candidateId = '0123456789abcdef0123456789abcdef';
  final List<VaultEntry> _entries = [];
  String? recoveredName;

  @override
  Future<List<VaultEntry>> listEntries() async {
    if (_entries.isEmpty) {
      throw StateError('Vault index is unreadable.');
    }
    return List.unmodifiable(_entries);
  }

  @override
  Future<List<VaultOrphanCandidate>> findRecoverableFiles() async => [
        VaultOrphanCandidate(
          id: candidateId,
          sizeBytes: 32,
          createdAt: DateTime.utc(2026, 11, 6),
          indexWasCorrupt: true,
        ),
      ];

  @override
  Future<VaultEntry> recoverOrphanedEntry({
    required String id,
    required String recoveredName,
  }) async {
    if (id != candidateId) throw StateError('Unexpected recovery candidate.');
    this.recoveredName = recoveredName;
    final entry = VaultEntry(
      id: id,
      name: recoveredName,
      sizeBytes: 32,
      createdAt: DateTime.utc(2026, 11, 6),
    );
    _entries.add(entry);
    return entry;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets(
    'customer can review and confirm an authenticated file when the index is corrupt',
    (tester) async {
      final vault = _RecoveryFlowVault();

      await tester.pumpWidget(
        MaterialApp(home: EncryptedVaultScreen(vault: vault)),
      );

      // Let the screen's initState-triggered asynchronous refresh finish
      // outside the fake-async zone. The fake vault performs no filesystem or
      // platform-channel work, so this only drains its Future continuations.
      await tester.runAsync(() async {
        await Future<void>.delayed(Duration.zero);
      });
      await tester.pump();
      await tester.pumpAndSettle();

      expect(find.textContaining('vault index could not be read'), findsOneWidget);
      expect(find.text('Verified encrypted file'), findsOneWidget);
      expect(find.text('Review'), findsOneWidget);

      await tester.tap(find.text('Review'));
      await tester.pump();
      await tester.enterText(find.byType(TextField), 'customer-recovered.txt');
      await tester.tap(find.text('Recover listing'));
      await tester.pump();

      expect(find.text('Confirm vault recovery'), findsOneWidget);
      await tester.tap(find.text('Confirm recovery'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));

      expect(vault.recoveredName, 'customer-recovered.txt');
      expect(find.text('customer-recovered.txt'), findsOneWidget);
      expect(find.textContaining('vault index could not be read'), findsNothing);
    },
  );
}
