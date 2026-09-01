import 'dart:convert';

import 'package:http/http.dart' as http;

import 'auth_api_contract.dart';
import 'auth_session.dart';

/// HTTPS JSON implementation of the Neon Shield authentication contract.
class HttpAuthApi implements AuthApiContract {
  HttpAuthApi({
    required String baseUrl,
    http.Client? client,
  })  : _baseUri = Uri.parse(baseUrl),
        _client = client ?? http.Client();

  final Uri _baseUri;
  final http.Client _client;

  Uri _uri(String path) => _baseUri.resolve(path);

  Map<String, dynamic> _decode(http.Response response) {
    final value = jsonDecode(response.body);
    if (value is! Map<String, dynamic>) {
      throw const AuthServiceException(AuthFailure.unavailable);
    }
    return value;
  }

  AuthFailure _failureFor(String? value) {
    for (final failure in AuthFailure.values) {
      if (failure.name == value) return failure;
    }
    return AuthFailure.unavailable;
  }

  AuthSession _sessionFrom(Map<String, dynamic> payload) {
    final raw = payload['session'];
    if (raw is! Map<String, dynamic>) {
      throw const AuthServiceException(AuthFailure.unavailable);
    }
    final token = raw['session_id'];
    final expiresAt = raw['expires_at'];
    final deviceId = raw['device_id'];
    if (token is! String || token.isEmpty ||
        expiresAt is! String || deviceId is! String || deviceId.isEmpty) {
      throw const AuthServiceException(AuthFailure.unavailable);
    }
    try {
      return AuthSession(
        token: token,
        expiresAt: DateTime.parse(expiresAt).toUtc(),
        deviceId: deviceId,
      );
    } on FormatException {
      throw const AuthServiceException(AuthFailure.unavailable);
    }
  }

  Future<AuthSession> _postSession(
    String path,
    Map<String, dynamic> body, {
    String? token,
  }) async {
    try {
      final headers = <String, String>{'Content-Type': 'application/json'};
      if (token != null) headers['Authorization'] = 'Bearer $token';
      final response = await _client.post(
        _uri(path),
        headers: headers,
        body: jsonEncode(body),
      );
      final payload = response.body.isEmpty ? <String, dynamic>{} : _decode(response);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw AuthServiceException(_failureFor(payload['error'] as String?));
      }
      return _sessionFrom(payload);
    } on AuthServiceException {
      rethrow;
    } on FormatException {
      throw const AuthServiceException(AuthFailure.unavailable);
    } on http.ClientException {
      throw const AuthServiceException(AuthFailure.unavailable);
    }
  }

  @override
  Future<AuthSession> signIn({
    required String identity,
    required String credential,
    required String deviceId,
  }) => _postSession('/v1/auth/sign-in', {
        'identity': identity,
        'credential': credential,
        'device_id': deviceId,
      });

  @override
  Future<AuthSession> refresh(AuthSession session) =>
      _postSession('/v1/auth/refresh', const {}, token: session.token);

  @override
  Future<void> revoke(AuthSession session) async {
    try {
      final response = await _client.post(
        _uri('/v1/auth/logout'),
        headers: {'Authorization': 'Bearer ${session.token}'},
      );
      if (response.statusCode != 204 && response.statusCode != 200) {
        final payload = response.body.isEmpty ? <String, dynamic>{} : _decode(response);
        throw AuthServiceException(_failureFor(payload['error'] as String?));
      }
    } on AuthServiceException {
      rethrow;
    } on http.ClientException {
      throw const AuthServiceException(AuthFailure.unavailable);
    } on FormatException {
      throw const AuthServiceException(AuthFailure.unavailable);
    }
  }

  @override
  Future<bool> isDeviceTrusted(AuthSession session) async {
    // The current backend contract validates trusted-device state whenever
    // an authenticated session is loaded/refreshed. Until a dedicated
    // trusted-device endpoint exists, a successful refresh is the authoritative
    // check and avoids inventing a client-side security authority.
    try {
      final refreshed = await refresh(session);
      return refreshed.deviceId == session.deviceId;
    } on AuthServiceException catch (error) {
      if (error.failure == AuthFailure.untrustedDevice ||
          error.failure == AuthFailure.revokedSession ||
          error.failure == AuthFailure.expiredSession ||
          error.failure == AuthFailure.invalidCredentials) {
        return false;
      }
      rethrow;
    }
  }
}
