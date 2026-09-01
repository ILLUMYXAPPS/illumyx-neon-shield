import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'auth_session.dart';

/// Platform-backed secure persistence for the current auth session.
///
/// Session tokens are credentials and must not be persisted in plain
/// SharedPreferences. The server remains authoritative for session validity.
class SecureAuthSessionStore implements AuthSessionStore {
  SecureAuthSessionStore({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  static const _key = 'neon_shield.auth_session';
  final FlutterSecureStorage _storage;

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
      if (token is! String || token.isEmpty ||
          expiresAt is! String || deviceId is! String || deviceId.isEmpty) {
        await clear();
        return null;
      }

      return AuthSession(
        token: token,
        expiresAt: DateTime.parse(expiresAt).toUtc(),
        deviceId: deviceId,
      );
    } on FormatException {
      await clear();
      return null;
    } on TypeError {
      await clear();
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
