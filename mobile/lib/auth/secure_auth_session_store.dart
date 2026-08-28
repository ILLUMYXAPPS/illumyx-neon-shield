import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'auth_session.dart';

/// Small provider-neutral storage boundary so the auth store can be tested
/// without implementing FlutterSecureStorage's platform-specific API.
abstract interface class AuthSecretStorage {
  Future<String?> read({required String key});
  Future<void> write({required String key, required String value});
  Future<void> delete({required String key});
}

class FlutterAuthSecretStorage implements AuthSecretStorage {
  FlutterAuthSecretStorage({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  @override
  Future<String?> read({required String key}) => _storage.read(key: key);

  @override
  Future<void> write({required String key, required String value}) =>
      _storage.write(key: key, value: value);

  @override
  Future<void> delete({required String key}) => _storage.delete(key: key);
}

/// Secure platform-backed persistence adapter for the auth boundary.
///
/// The server remains authoritative for authorization. This store only keeps
/// the session material needed to resume a client session securely.
class SecureAuthSessionStore implements AuthSessionStore {
  SecureAuthSessionStore({AuthSecretStorage? storage})
      : _storage = storage ?? FlutterAuthSecretStorage();

  static const _key = 'neon_shield.auth_session';
  final AuthSecretStorage _storage;

  @override
  Future<AuthSession?> read() async {
    final raw = await _storage.read(key: _key);
    if (raw == null) return null;

    try {
      final json = jsonDecode(raw);
      if (json is! Map<String, dynamic>) return null;
      final token = json['token'];
      final expiresAt = json['expiresAt'];
      final deviceId = json['deviceId'];
      if (token is! String || expiresAt is! String || deviceId is! String) {
        return null;
      }

      return AuthSession(
        token: token,
        expiresAt: DateTime.parse(expiresAt).toUtc(),
        deviceId: deviceId,
      );
    } on FormatException {
      return null;
    }
  }

  @override
  Future<void> write(AuthSession session) async {
    await _storage.write(
      key: _key,
      value: jsonEncode({
        'token': session.token,
        'expiresAt': session.expiresAt.toUtc().toIso8601String(),
        'deviceId': session.deviceId,
      }),
    );
  }

  @override
  Future<void> clear() => _storage.delete(key: _key);
}
