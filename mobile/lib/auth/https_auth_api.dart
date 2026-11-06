import 'dart:convert';

import 'package:http/http.dart' as http;

import 'auth_api_contract.dart';
import 'auth_service.dart';
import 'auth_session.dart';
import 'device_pairing_api.dart';

/// HTTPS implementation of authentication and device-pairing contracts.
class HttpsAuthApi implements AuthApiContract, DevicePairingApi {
  HttpsAuthApi({
    required Uri baseUri,
    http.Client? client,
    Duration requestTimeout = const Duration(seconds: 15),
  })  : _baseUri = _validateBaseUri(baseUri),
        _client = client ?? http.Client(),
        _requestTimeout = requestTimeout {
    if (requestTimeout <= Duration.zero) {
      throw ArgumentError.value(requestTimeout, 'requestTimeout', 'Must be positive');
    }
  }

  final Uri _baseUri;
  final http.Client _client;
  final Duration _requestTimeout;

  Future<http.Response> _send(Future<http.Response> request) {
    return request.timeout(
      _requestTimeout,
      onTimeout: () => throw const AuthServiceException(AuthFailure.unavailable),
    );
  }

  static Uri _validateBaseUri(Uri uri) {
    final isLoopback = uri.host == '127.0.0.1' || uri.host == 'localhost' || uri.host == '::1';
    if (uri.scheme != 'https' && !isLoopback) {
      throw ArgumentError('Neon Shield auth API requires HTTPS');
    }
    if (uri.host.isEmpty || uri.userInfo.isNotEmpty) {
      throw ArgumentError('Neon Shield auth API requires a valid host without user info');
    }
    return uri;
  }

  Uri _endpoint(String path) => _baseUri.resolve(path);

  @override
  Future<AuthSession> signIn({
    required String identity,
    required String credential,
    required String deviceId,
  }) async {
    final response = await _send(_client.post(
      _endpoint('/v1/auth/sign-in'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'identity': identity, 'credential': credential, 'device_id': deviceId}),
    ));
    return _sessionFromResponse(response);
  }

  @override
  Future<AuthSession> refresh(AuthSession session) async {
    final response = await _send(_client.post(_endpoint('/v1/auth/refresh'), headers: _authHeaders(session)));
    return _sessionFromResponse(response);
  }

  @override
  Future<void> revoke(AuthSession session) async {
    final response = await _send(_client.post(_endpoint('/v1/auth/logout'), headers: _authHeaders(session)));
    if (response.statusCode != 204 && response.statusCode != 200) throw _failure(response);
  }

  @override
  Future<bool> isDeviceTrusted(AuthSession session) async {
    final response = await _send(_client.post(_endpoint('/v1/auth/trusted-device'), headers: _authHeaders(session)));
    if (response.statusCode != 200) throw _failure(response);
    final trusted = _decodeObject(response.body)['trusted'];
    if (trusted is! bool) throw const AuthServiceException(AuthFailure.unavailable);
    return trusted;
  }

  @override
  Future<DevicePairingRequest> startPairing({
    required String identity,
    required String credential,
    required String deviceId,
    required String deviceName,
  }) async {
    final response = await _send(_client.post(
      _endpoint('/v1/device-pairing/start'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'identity': identity,
        'credential': credential,
        'device_id': deviceId,
        'device_name': deviceName,
      }),
    ));
    if (response.statusCode != 201) throw _failure(response);
    final data = _decodeObject(response.body);
    try {
      final requestId = data['request_id'];
      final code = data['pairing_code'];
      final secret = data['pairing_secret'];
      final expires = data['expires_at'];
      if (requestId is! String || code is! String || secret is! String ||
          expires is! String) {
        throw const FormatException();
      }
      return DevicePairingRequest(
        requestId: requestId,
        code: code,
        secret: secret,
        expiresAt: DateTime.parse(expires).toUtc(),
      );
    } on FormatException {
      throw const AuthServiceException(AuthFailure.unavailable);
    }
  }

  @override
  Future<String> pairingStatus({required String requestId, required String secret}) async {
    final response = await _send(_client.post(
      _endpoint('/v1/device-pairing/status'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'request_id': requestId, 'pairing_secret': secret}),
    ));
    if (response.statusCode != 200) throw _failure(response);
    final status = _decodeObject(response.body)['status'];
    if (status is! String || !{'pending', 'approved', 'expired', 'rejected'}.contains(status)) {
      throw const AuthServiceException(AuthFailure.unavailable);
    }
    return status;
  }

  @override
  Future<void> approvePairing({
    required AuthSession session,
    required String requestId,
    required String code,
  }) async {
    final response = await _send(_client.post(
      _endpoint('/v1/device-pairing/approve'),
      headers: _authHeaders(session),
      body: jsonEncode({'request_id': requestId, 'pairing_code': code}),
    ));
    if (response.statusCode != 200) throw _failure(response);
  }

  @override
  Future<List<ConnectedDevice>> listDevices(AuthSession session) async {
    final response = await _send(_client.get(_endpoint('/v1/devices'), headers: _authHeaders(session)));
    if (response.statusCode != 200) throw _failure(response);
    final values = _decodeObject(response.body)['devices'];
    if (values is! List) throw const AuthServiceException(AuthFailure.unavailable);
    try {
      return values.map((value) {
        if (value is! Map) throw const FormatException();
        final reference = value['device_ref'];
        final name = value['device_name'];
        final addedAt = value['added_at'];
        if (reference is! String || name is! String || addedAt is! String) {
          throw const FormatException();
        }
        return ConnectedDevice(
          reference: reference,
          name: name,
          addedAt: DateTime.parse(addedAt).toLocal(),
        );
      }).toList(growable: false);
    } on FormatException {
      throw const AuthServiceException(AuthFailure.unavailable);
    }
  }

  @override
  Future<void> renameDevice({
    required AuthSession session,
    required String deviceReference,
    required String deviceName,
  }) async {
    final response = await _send(_client.patch(
      _endpoint('/v1/devices/$deviceReference'),
      headers: _authHeaders(session),
      body: jsonEncode({'device_name': deviceName}),
    ));
    if (response.statusCode != 200) throw _failure(response);
  }

  @override
  Future<void> unlinkDevice({
    required AuthSession session,
    required String deviceReference,
  }) async {
    final response = await _send(_client.delete(
      _endpoint('/v1/devices/$deviceReference'),
      headers: _authHeaders(session),
    ));
    if (response.statusCode != 204) throw _failure(response);
  }

  Map<String, String> _authHeaders(AuthSession session) => {
        'Authorization': 'Bearer ${session.token}',
        'Content-Type': 'application/json',
      };

  AuthSession _sessionFromResponse(http.Response response) {
    if (response.statusCode != 200) throw _failure(response);
    final session = _decodeObject(response.body)['session'];
    if (session is! Map) throw const AuthServiceException(AuthFailure.unavailable);
    try {
      final token = session['session_id'];
      final expiresAtValue = session['expires_at'];
      final deviceId = session['device_id'];
      if (token is! String || token.trim().isEmpty || expiresAtValue is! String ||
          deviceId is! String || deviceId.trim().isEmpty) {
        throw const FormatException();
      }
      final expiresAt = DateTime.parse(expiresAtValue).toUtc();
      if (!expiresAt.isAfter(DateTime.now().toUtc())) throw const FormatException();
      return AuthSession(token: token, expiresAt: expiresAt, deviceId: deviceId);
    } on FormatException {
      throw const AuthServiceException(AuthFailure.unavailable);
    }
  }

  Map<String, dynamic> _decodeObject(String body) {
    try {
      final value = jsonDecode(body);
      if (value is Map<String, dynamic>) return value;
    } on FormatException {
      // Malformed server responses fail closed.
    }
    throw const AuthServiceException(AuthFailure.unavailable);
  }

  AuthServiceException _failure(http.Response response) {
    try {
      switch (_decodeObject(response.body)['error']) {
        case 'invalid_credentials':
          return const AuthServiceException(AuthFailure.invalidCredentials);
        case 'expired_session':
          return const AuthServiceException(AuthFailure.expiredSession);
        case 'revoked_session':
          return const AuthServiceException(AuthFailure.revokedSession);
        case 'untrusted_device':
          return const AuthServiceException(AuthFailure.untrustedDevice);
        case 'blocked_identity':
          return const AuthServiceException(AuthFailure.blockedIdentity);
        case 'rate_limited':
          return const AuthServiceException(AuthFailure.rateLimited);
        default:
          return const AuthServiceException(AuthFailure.unavailable);
      }
    } on AuthServiceException {
      return const AuthServiceException(AuthFailure.unavailable);
    }
  }
}
