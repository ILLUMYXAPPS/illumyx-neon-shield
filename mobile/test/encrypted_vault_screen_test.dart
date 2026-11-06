import 'dart:async';

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
  final Completer<List<VaultEntry>> indexRead = Completer<List<VaultEntry>>();
  final Completer<List<VaultOrphanCandidate>> recoveryScan =
      Completer<List<VaultOrphanCandidate>>();
  String? recoveredName;

  @override
  Future<List<VaultEntry>> listEntries() {
    if (_entries.isNotEmpty) return Future.value(List.unmodifiable(_entries));
    return indexRead.future;
  }

  @override
  Future<List<VaultOrphanCandidate>> findRecoverableFiles() =>
      recoveryScan.future;

  List<VaultOrphanCandidate> get recoveryCandidates => [
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

      // Drive the two asynchronous reads explicitly. This verifies that the
      // screen waits for the corrupt-index result, starts recovery discovery,
      // and renders the authenticated candidate only after that scan returns.
      await tester.pump();
      vault.indexRead.completeError(StateError('Vault index is unreadable.'));
      await tester.pump();
      vault.recoveryScan.complete(vault.recoveryCandidates);
      await tester.pump();
      await tester.pumpAndSettle();

      expect(find.textContaining('vault index could not be read'), findsOneWidget);
      // The recovery card is below the vault introduction in a scrolling
      // ListView. Bring it into the viewport before asserting on its title.
      await tester.scrollUntilVisible(
        find.text('Verified encrypted file'),
        200,
        scrollable: find.byType(Scrollable),
      );
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
