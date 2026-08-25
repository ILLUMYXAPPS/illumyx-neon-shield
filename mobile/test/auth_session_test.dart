import 'package:flutter_test/flutter_test.dart';
import 'package:illumyx_neon_shield/auth/auth_session.dart';

void main() {
  test('session is valid before expiry', () {
    final session = AuthSession(
      token: 'server-token',
      expiresAt: DateTime.now().toUtc().add(const Duration(minutes: 5)),
      deviceId: 'trusted-device',
    );

    expect(session.isExpired, isFalse);
  });

  test('expired session is rejected locally', () {
    final session = AuthSession(
      token: 'server-token',
      expiresAt: DateTime.now().toUtc().subtract(const Duration(seconds: 1)),
      deviceId: 'trusted-device',
    );

    expect(session.isExpired, isTrue);
  });

  test('session carries server-issued token and device identity', () {
    final expiry = DateTime.utc(2026, 8, 25, 4);
    final session = AuthSession(
      token: 'opaque-server-token',
      expiresAt: expiry,
      deviceId: 'device-123',
    );

    expect(session.token, 'opaque-server-token');
    expect(session.expiresAt, expiry);
    expect(session.deviceId, 'device-123');
  });
}
