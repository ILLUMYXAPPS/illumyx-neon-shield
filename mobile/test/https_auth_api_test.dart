import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:illumyx_neon_shield/auth/auth_api_contract.dart';
import 'package:illumyx_neon_shield/auth/auth_service.dart';
import 'package:illumyx_neon_shield/auth/auth_session.dart';
import 'package:illumyx_neon_shield/auth/https_auth_api.dart';

void main() {
  final session = AuthSession(
    token: 'session-123',
    expiresAt: DateTime.utc(2026, 12, 1),
    deviceId: 'device-123',
  );

  test('rejects non-HTTPS production endpoints', () {
    expect(
      () => HttpsAuthApi(baseUri: Uri.parse('http://example.invalid')),
      throwsArgumentError,
    );
  });

  test('rejects endpoint URLs containing user info', () {
    expect(
      () => HttpsAuthApi(baseUri: Uri.parse('https://user:password@example.invalid')),
      throwsArgumentError,
    );
  });

  test('allows loopback HTTP for local development', () {
    expect(
      HttpsAuthApi(baseUri: Uri.parse('http://127.0.0.1:8080')),
      isA<HttpsAuthApi>(),
    );
  });

  test('signIn posts the expected payload and parses the session', () async {
    late http.Request request;
    final client = MockClient((incoming) async {
      request = incoming;
      return http.Response(
        jsonEncode({
          'session': {
            'session_id': session.token,
            'expires_at': session.expiresAt.toIso8601String(),
            'device_id': session.deviceId,
          },
        }),
        200,
      );
    });

    final api = HttpsAuthApi(
      baseUri: Uri.parse('https://example.invalid'),
      client: client,
    );

    final result = await api.signIn(
      identity: 'user@example.com',
      credential: 'secret',
      deviceId: session.deviceId,
    );

    expect(request.method, 'POST');
    expect(request.url.path, '/v1/auth/sign-in');
    expect(jsonDecode(request.body), {
      'identity': 'user@example.com',
      'credential': 'secret',
      'device_id': 'device-123',
    });
    expect(result.token, session.token);
    expect(result.deviceId, session.deviceId);
  });


  test('maps a stalled authentication request to unavailable after timeout', () async {
    final pending = Completer<http.Response>();
    final client = MockClient((_) => pending.future);
    final api = HttpsAuthApi(
      baseUri: Uri.parse('https://example.invalid'),
      client: client,
      requestTimeout: const Duration(milliseconds: 10),
    );

    await expectLater(
      api.signIn(
        identity: 'user@example.com',
        credential: 'secret',
        deviceId: session.deviceId,
      ),
      throwsA(isA<AuthServiceException>().having(
        (error) => error.failure,
        'failure',
        AuthFailure.unavailable,
      )),
    );
  });

  test('rejects a successful response with an empty session token', () async {
    final client = MockClient((_) async => http.Response(
          jsonEncode({
            'session': {
              'session_id': '',
              'expires_at': DateTime.now().toUtc().add(const Duration(minutes: 5)).toIso8601String(),
              'device_id': 'device-123',
            },
          }),
          200,
        ));
    final api = HttpsAuthApi(baseUri: Uri.parse('https://example.invalid'), client: client);

    await expectLater(
      api.signIn(identity: 'user@example.com', credential: 'secret', deviceId: 'device-123'),
      throwsA(isA<AuthServiceException>().having(
        (error) => error.failure,
        'failure',
        AuthFailure.unavailable,
      )),
    );
  });

  test('rejects a successful response with an expired session', () async {
    final client = MockClient((_) async => http.Response(
          jsonEncode({
            'session': {
              'session_id': 'session-123',
              'expires_at': DateTime.now().toUtc().subtract(const Duration(seconds: 1)).toIso8601String(),
              'device_id': 'device-123',
            },
          }),
          200,
        ));
    final api = HttpsAuthApi(baseUri: Uri.parse('https://example.invalid'), client: client);

    await expectLater(
      api.signIn(identity: 'user@example.com', credential: 'secret', deviceId: 'device-123'),
      throwsA(isA<AuthServiceException>().having(
        (error) => error.failure,
        'failure',
        AuthFailure.unavailable,
      )),
    );
  });

  test('trusted-device check sends bearer authentication', () async {
    late http.Request request;
    final client = MockClient((incoming) async {
      request = incoming;
      return http.Response(jsonEncode({'trusted': true}), 200);
    });

    final api = HttpsAuthApi(
      baseUri: Uri.parse('https://example.invalid'),
      client: client,
    );

    expect(await api.isDeviceTrusted(session), isTrue);
    expect(request.url.path, '/v1/auth/trusted-device');
    expect(request.headers['authorization'], 'Bearer session-123');
  });

  test('maps invalid credentials to the typed auth failure', () async {
    final client = MockClient((_) async => http.Response(
          jsonEncode({'error': 'invalid_credentials'}),
          401,
        ));

    final api = HttpsAuthApi(
      baseUri: Uri.parse('https://example.invalid'),
      client: client,
    );

    await expectLater(
      api.signIn(
        identity: 'user@example.com',
        credential: 'wrong',
        deviceId: session.deviceId,
      ),
      throwsA(isA<AuthServiceException>().having(
        (error) => error.failure,
        'failure',
        AuthFailure.invalidCredentials,
      )),
    );
  });

  test('maps blocked identities to the typed auth failure', () async {
    final client = MockClient((_) async => http.Response(
          jsonEncode({'error': 'blocked_identity'}),
          403,
        ));
    final api = HttpsAuthApi(baseUri: Uri.parse('https://example.invalid'), client: client);

    await expectLater(
      api.signIn(
        identity: 'blocked@example.com',
        credential: 'secret',
        deviceId: session.deviceId,
      ),
      throwsA(isA<AuthServiceException>().having(
        (error) => error.failure,
        'failure',
        AuthFailure.blockedIdentity,
      )),
    );
  });
}
