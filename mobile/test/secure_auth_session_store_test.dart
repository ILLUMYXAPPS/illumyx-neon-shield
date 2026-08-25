import 'package:flutter_test/flutter_test.dart';
import 'package:illumyx_neon_shield/auth/auth_session.dart';
import 'package:illumyx_neon_shield/auth/secure_auth_session_store.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
  });

  test('writes and restores a session', () async {
    final store = SharedPreferencesAuthSessionStore();
    final session = AuthSession(
      token: 'opaque-server-token',
      expiresAt: DateTime.utc(2026, 8, 25, 5),
      deviceId: 'device-123',
    );

    await store.write(session);
    final restored = await store.read();

    expect(restored, isNotNull);
    expect(restored!.token, session.token);
    expect(restored.expiresAt, session.expiresAt);
    expect(restored.deviceId, session.deviceId);
  });

  test('returns null for malformed stored session', () async {
    SharedPreferences.setMockInitialValues({
      'neon_shield.auth_session': '{not-json}',
    });
    final store = SharedPreferencesAuthSessionStore();

    expect(await store.read(), isNull);
  });

  test('clears a stored session', () async {
    final store = SharedPreferencesAuthSessionStore();
    await store.write(
      AuthSession(
        token: 'opaque-server-token',
        expiresAt: DateTime.utc(2026, 8, 25, 5),
        deviceId: 'device-123',
      ),
    );

    await store.clear();

    expect(await store.read(), isNull);
  });
}
