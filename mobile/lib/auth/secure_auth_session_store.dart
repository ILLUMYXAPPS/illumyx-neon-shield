import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import 'auth_session.dart';

/// Persistence adapter for the auth boundary.
///
/// This adapter is intentionally small and isolated so the storage mechanism
/// can be replaced with platform secure storage before production release.
/// It must not be treated as proof that a session is still authorized: the
/// server remains authoritative and [AuthSession.isExpired] is checked before
/// a restored session is used.
class SharedPreferencesAuthSessionStore implements AuthSessionStore {
  SharedPreferencesAuthSessionStore({SharedPreferences? preferences})
      : _preferences = preferences;

  static const _key = 'neon_shield.auth_session';
  SharedPreferences? _preferences;

  Future<SharedPreferences> get _prefs async =>
      _preferences ??= await SharedPreferences.getInstance();

  @override
  Future<AuthSession?> read() async {
    final raw = (await _prefs).getString(_key);
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
    await (await _prefs).setString(
      _key,
      jsonEncode({
        'token': session.token,
        'expiresAt': session.expiresAt.toUtc().toIso8601String(),
        'deviceId': session.deviceId,
      }),
    );
  }

  @override
  Future<void> clear() async {
    await (await _prefs).remove(_key);
  }
}
