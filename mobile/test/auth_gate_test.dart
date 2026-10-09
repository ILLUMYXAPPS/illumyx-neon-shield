import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:illumyx_neon_shield/auth/auth_api_contract.dart';
import 'package:illumyx_neon_shield/auth/auth_gate.dart';
import 'package:illumyx_neon_shield/auth/auth_service.dart';
import 'package:illumyx_neon_shield/auth/auth_session.dart';

class _FakeAuthService implements AuthService {
  AuthSession? current;
  bool trusted = true;

  AuthSession _newSession({Duration lifetime = const Duration(minutes: 10)}) => AuthSession(
        token: 'server-session-token',
        expiresAt: DateTime.now().toUtc().add(lifetime),
        deviceId: 'device-1',
      );

  @override
  Future<AuthSession> signIn({
    required String identity,
    required String credential,
    required String deviceId,
  }) async {
    if (identity != 'owner@example.test' || credential != 'correct-password') {
      throw const AuthServiceException(AuthFailure.invalidCredentials);
    }
    if (!trusted) {
      throw const AuthServiceException(AuthFailure.untrustedDevice);
    }
    current = _newSession();
    return current!;
  }

  @override
  Future<AuthSession?> restoreSession() async => current;

  @override
  Future<void> signOut(AuthSession session) async {
    current = null;
  }
}

void main() {
  testWidgets('dashboard remains hidden until server sign-in succeeds', (tester) async {
    final service = _FakeAuthService();

    await tester.pumpWidget(MaterialApp(
      home: AuthGate(
        authService: service,
        deviceIdProvider: () async => 'device-1',
        dashboardBuilder: (_) => const Scaffold(body: Text('AUTHENTICATED DASHBOARD')),
      ),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Sign in securely'), findsOneWidget);
    expect(find.text('AUTHENTICATED DASHBOARD'), findsNothing);

    await tester.enterText(find.byType(TextField).at(0), 'owner@example.test');
    await tester.enterText(find.byType(TextField).at(1), 'correct-password');
    await tester.tap(find.text('Sign in securely'));
    await tester.pumpAndSettle();

    expect(find.text('AUTHENTICATED DASHBOARD'), findsOneWidget);
  });

  testWidgets('untrusted device cannot open dashboard', (tester) async {
    final service = _FakeAuthService()..trusted = false;

    await tester.pumpWidget(MaterialApp(
      home: AuthGate(
        authService: service,
        deviceIdProvider: () async => 'device-1',
        dashboardBuilder: (_) => const Scaffold(body: Text('AUTHENTICATED DASHBOARD')),
      ),
    ));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).at(0), 'owner@example.test');
    await tester.enterText(find.byType(TextField).at(1), 'correct-password');
    await tester.tap(find.text('Sign in securely'));
    await tester.pumpAndSettle();

    expect(find.text('This device has not been approved for this account.'), findsOneWidget);
    expect(find.text('AUTHENTICATED DASHBOARD'), findsNothing);
  });

  testWidgets('restored server session is required before dashboard is shown', (tester) async {
    final service = _FakeAuthService()..current = AuthSession(
      token: 'restored-session',
      expiresAt: DateTime.now().toUtc().add(const Duration(minutes: 5)),
      deviceId: 'device-1',
    );

    await tester.pumpWidget(MaterialApp(
      home: AuthGate(
        authService: service,
        deviceIdProvider: () async => 'device-1',
        dashboardBuilder: (_) => const Scaffold(body: Text('AUTHENTICATED DASHBOARD')),
      ),
    ));
    await tester.pumpAndSettle();

    expect(find.text('AUTHENTICATED DASHBOARD'), findsOneWidget);
  });

  testWidgets('dashboard locks automatically when session expires', (tester) async {
    final service = _FakeAuthService()
      ..current = AuthSession(
        token: 'short-session',
        expiresAt: DateTime.now().toUtc().add(const Duration(seconds: 2)),
        deviceId: 'device-1',
      );

    await tester.pumpWidget(MaterialApp(
      home: AuthGate(
        authService: service,
        deviceIdProvider: () async => 'device-1',
        dashboardBuilder: (_) => const Scaffold(body: Text('AUTHENTICATED DASHBOARD')),
      ),
    ));
    await tester.pumpAndSettle();

    expect(find.text('AUTHENTICATED DASHBOARD'), findsOneWidget);

    await tester.pump(const Duration(seconds: 3));
    await tester.pump();

    expect(find.text('AUTHENTICATED DASHBOARD'), findsNothing);
    expect(find.text('Your session has expired. Please sign in again.'), findsOneWidget);
    expect(find.text('Sign in securely'), findsOneWidget);
  });
}
