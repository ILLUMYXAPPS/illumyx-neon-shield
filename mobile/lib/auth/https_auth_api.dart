import 'dart:convert';

import 'package:http/http.dart' as http;

import 'auth_api_contract.dart';
import 'auth_service.dart';
import 'auth_session.dart';

/// HTTPS implementation of the Neon Shield authentication contract.
///
/// The caller must provide an HTTPS base URL in production. Plain HTTP is
/// rejected except for loopback hosts used by local development/tests.
class HttpsAuthApi implements AuthApiContract {
  HttpsAuthApi({required Uri baseUri, http.Client? client})
      : _baseUri = _validateBaseUri(baseUri),
        _client = client ?? http.Client();

  final Uri _baseUri;
  final http.Client _client;

  static Uri _validateBaseUri(Uri uri) {
    final isLoopback = uri.host == '127.0.0.1' || uri.host == 'localhost' || uri.host == '::1';
    if (uri.scheme != 'https' && !isLoopback) {
      throw ArgumentError('Neon Shield auth API requires HTTPS');
    }
    return uri;
  }

  Uri _endpoint(String path) => _baseUri.resolve(path);

  @override
  Future<AuthSession> signIn({required String identity, required String credential, required String deviceId}) async {
    final response = await _client.post(
      _endpoint('/v1/auth/sign-in'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'identity': identity, 'credential': credential, 'device_id': deviceId}),
    );
    return _sessionFromResponse(response);
  }

  @override
  Future<AuthSession> refresh(AuthSession session) async {
    final response = await _client.post(_endpoint('/v1/auth/refresh'), headers: _authHeaders(session));
    return _sessionFromResponse(response);
  }

  @override
  Future<void> revoke(AuthSession session) async {
    final response = await _client.post(_endpoint('/v1/auth/logout'), headers: _authHeaders(session));
    if (response.statusCode != 204 && response.statusCode != 200) throw _failure(response);
  }

  @override
  Future<bool> isDeviceTrusted(AuthSession session) async {
    final response = await _client.post(_endpoint('/v1/auth/trusted-device'), headers: _authHeaders(session));
    if (response.statusCode != 200) throw _failure(response);
    final data = _decodeObject(response.body);
    final trusted = data['trusted'];
    if (trusted is! bool) throw const AuthServiceException(AuthFailure.unavailable);
    return trusted;
  }

  Map<String, String> _authHeaders(AuthSession session) => {
        'Authorization': 'Bearer ${session.token}',
        'Content-Type': 'application/json',
      };

  AuthSession _sessionFromResponse(http.Response response) {
    if (response.statusCode != 200) throw _failure(response);
    final data = _decodeObject(response.body);
    final session = data['session'];
    if (session is! Map) throw const AuthServiceException(AuthFailure.unavailable);
    try {
      final token = session['session_id'];
      final expiresAt = session['expires_at'];
      final deviceId = session['device_id'];
      if (token is! String || expiresAt is! String || deviceId is! String) throw const FormatException();
      return AuthSession(token: token, expiresAt: DateTime.parse(expiresAt).toUtc(), deviceId: deviceId);
    } on FormatException {
      throw const AuthServiceException(AuthFailure.unavailable);
    }
  }

  Map<String, dynamic> _decodeObject(String body) {
    try {
      final value = jsonDecode(body);
      if (value is Map<String, dynamic>) return value;
    } on FormatException {
      // Malformed server responses are deliberately mapped to a safe failure.
    }
    throw const AuthServiceException(AuthFailure.unavailable);
  }

  AuthServiceException _failure(http.Response response) {
    try {
      final data = _decodeObject(response.body);
      switch (data['error']) {
        case 'invalid_credentials': return const AuthServiceException(AuthFailure.invalidCredentials);
        case 'expired_session': return const AuthServiceException(AuthFailure.expiredSession);
        case 'revoked_session': return const AuthServiceException(AuthFailure.revokedSession);
        case 'untrusted_device': return const AuthServiceException(AuthFailure.untrustedDevice);
        case 'rate_limited': return const AuthServiceException(AuthFailure.rateLimited);
        default: return const AuthServiceException(AuthFailure.unavailable);
      }
    } on AuthServiceException {
      return const AuthServiceException(AuthFailure.unavailable);
    }
  }
}
