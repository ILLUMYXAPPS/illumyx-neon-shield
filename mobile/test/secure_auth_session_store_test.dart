import 'package:flutter_test/flutter_test.dart';
import 'package:illumyx_neon_shield/auth/auth_session.dart';
import 'package:illumyx_neon_shield/auth/secure_auth_session_store.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class InMemorySecureStorage implements FlutterSecureStorage {
  final Map<String, String> _values = {};

  @override
  Future<String?> read({required String key, Map<String, String>? options}) async => _values[key];

  @override
  Future<void> write({required String key, required String value, Map<String, String>? options}) async {
    _values[key] = value;
  }

  @override
  Future<void> delete({required String key, Map<String, String>? options}) async {
    _values.remove(key);
  }

  @override
  Future<void> deleteAll({Map<String, String>? options}) async => _values.clear();

  @override
  Future<Map<String, String>> readAll({Map<String, String>? options}) async => Map.unmodifiable(_values);

  @override
  Future<bool> containsKey({required String key, Map<String, String>? options}) async => _values.containsKey(key);

  @override
  Future<void> deleteWithResult({required String key, Map<String, String>? options}) async => _values.remove(key);
}

void main() {
  test('writes and restores a session', () async {
    final storage = InMemorySecureStorage();
    final store = SecureAuthSessionStore(storage: storage);
    final session = AuthSession(
      token: 'opaque-server-token',
      expiresAt: DateTime.utc(2026, 12, 25, 5),
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
    final storage = InMemorySecureStorage();
    await storage.write(key: 'neon_shield.auth_session', value: '{not-json}');
    final store = SecureAuthSessionStore(storage: storage);

    expect(await store.read(), isNull);
  });

  test('clears a stored session', () async {
    final storage = InMemorySecureStorage();
    final store = SecureAuthSessionStore(storage: storage);
    await store.write(
      AuthSession(
        token: 'opaque-server-token',
        expiresAt: DateTime.utc(2026, 12, 25, 5),
        deviceId: 'device-123',
      ),
    );

    await store.clear();

    expect(await store.read(), isNull);
  });
}
