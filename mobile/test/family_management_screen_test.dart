import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:illumyx_neon_shield/auth/auth_session.dart';
import 'package:illumyx_neon_shield/family/family_api.dart';
import 'package:illumyx_neon_shield/family/family_management_screen.dart';

class _FakeFamilyApi implements FamilyInvitationsApi {
  final pending = <FamilyInvitation>[];
  String? acceptedCode;
  int revoked = 0;

  @override
  Future<FamilyInvitation> create(AuthSession session) async {
    final invitation = FamilyInvitation(
      id: 'invite_1234567890123456',
      code: 'one-time-family-code',
      expiresAt: DateTime.utc(2026, 11, 15),
    );
    pending.add(invitation);
    return invitation;
  }

  @override
  Future<List<FamilyInvitation>> list(AuthSession session) async => List.of(pending);

  @override
  Future<void> accept(AuthSession session, String code) async {
    acceptedCode = code;
  }

  @override
  Future<bool> revoke(AuthSession session, String invitationId) async {
    revoked++;
    pending.removeWhere((item) => item.id == invitationId);
    return true;
  }
}

void main() {
  final session = AuthSession(
    token: 'family-session',
    expiresAt: DateTime.utc(2027),
    deviceId: 'device-1',
  );

  testWidgets('owner can create and view a one-time invitation', (tester) async {
    final api = _FakeFamilyApi();
    await tester.pumpWidget(MaterialApp(
      home: FamilyManagementScreen(api: api, session: session),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Family Management'), findsOneWidget);
    await tester.tap(find.text('Create invitation'));
    await tester.pumpAndSettle();

    expect(find.text('YOUR NEW INVITATION CODE'), findsOneWidget);
    expect(find.text('one-time-family-code'), findsOneWidget);
    expect(find.text('Copy code'), findsOneWidget);
    expect(find.text('Share invitation'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('PENDING INVITATIONS'),
      250,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('PENDING INVITATIONS'), findsOneWidget);
  });

  testWidgets('signed-in recipient can enter and accept a Family code', (tester) async {
    final api = _FakeFamilyApi();
    await tester.pumpWidget(MaterialApp(
      home: FamilyManagementScreen(api: api, session: session),
    ));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.byType(TextField),
      250,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.enterText(find.byType(TextField), 'recipient-family-code');
    await tester.pump();
    await tester.tap(find.text('Accept invitation'));
    await tester.pumpAndSettle();

    expect(api.acceptedCode, 'recipient-family-code');
    expect(find.text('You have joined the Family household.'), findsOneWidget);
  });

  testWidgets('owner can revoke a pending invitation', (tester) async {
    final api = _FakeFamilyApi();
    api.pending.add(FamilyInvitation(
      id: 'invite_1234567890123456',
      code: null,
      expiresAt: DateTime.utc(2026, 11, 15),
    ));
    await tester.pumpWidget(MaterialApp(
      home: FamilyManagementScreen(api: api, session: session),
    ));
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('Revoke invitation').first);
    await tester.pumpAndSettle();

    expect(api.revoked, 1);
    expect(find.text('Invitation revoked.'), findsOneWidget);
  });
}
