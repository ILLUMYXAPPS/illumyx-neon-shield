import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'auth_session.dart';

/// Secure platform-backed persistence adapter for the auth boundary.
///
/// The server remains authoritative for authorization. This store only keeps
/// the session material needed to resume a client session securely.
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
      if (token is! String || expiresAt is! String || deviceId is! String) {
        return null;
      }

      return AuthSession(
        token: token,
        expiresAt: DateTime.parse(expiresAt),
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
