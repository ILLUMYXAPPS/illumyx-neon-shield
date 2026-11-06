import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:illumyx_neon_shield/auth/auth_session.dart';
import 'package:illumyx_neon_shield/auth/device_pairing_api.dart';
import 'package:illumyx_neon_shield/auth/device_pairing_screen.dart';

class _FakePairingApi implements DevicePairingApi {
  @override
  Future<DevicePairingRequest> startPairing({
    required String identity,
    required String credential,
    required String deviceId,
    required String deviceName,
  }) async {
    return DevicePairingRequest(
      requestId: 'request-reference-123',
      code: '123456',
      secret: 'polling-secret',
      expiresAt: DateTime.now().toUtc().add(const Duration(minutes: 5)),
    );
  }

  @override
  Future<String> pairingStatus({required String requestId, required String secret}) async => 'pending';

  @override
  Future<void> approvePairing({
    required AuthSession session,
    required String requestId,
    required String code,
  }) async {}

  @override
  Future<List<ConnectedDevice>> listDevices(AuthSession session) async => const [];

  @override
  Future<void> renameDevice({
    required AuthSession session,
    required String deviceReference,
    required String deviceName,
  }) async {}

  @override
  Future<void> unlinkDevice({
    required AuthSession session,
    required String deviceReference,
  }) async {}
}

void main() {
  testWidgets('shows the six-digit manual pairing flow without QR instructions', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: DevicePairingScreen(
        api: _FakePairingApi(),
        deviceIdProvider: () async => 'new-test-device',
      ),
    ));

    expect(find.text('Pair this device'), findsOneWidget);
    expect(find.text('Start secure pairing'), findsOneWidget);

    await tester.enterText(find.byType(TextField).at(0), 'owner@example.test');
    await tester.enterText(find.byType(TextField).at(1), 'correct-password');
    await tester.enterText(find.byType(TextField).at(2), 'My test iPad');
    await tester.tap(find.text('Start secure pairing'));
    await tester.pumpAndSettle();

    expect(find.text('YOUR PAIRING CODE'), findsOneWidget);
    expect(find.text('123456'), findsOneWidget);
    expect(find.text('REQUEST REFERENCE'), findsOneWidget);
    expect(find.text('request-reference-123'), findsOneWidget);
    expect(find.textContaining('expires after five minutes'), findsOneWidget);
    expect(find.textContaining('enter this code plus the request reference below'), findsOneWidget);
    expect(find.textContaining('QR'), findsNothing);
    expect(find.textContaining('camera'), findsNothing);
  });
}
