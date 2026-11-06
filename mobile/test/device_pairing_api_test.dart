import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:illumyx_neon_shield/auth/auth_session.dart';
import 'package:illumyx_neon_shield/auth/https_auth_api.dart';

void main() {
  final session = AuthSession(
    token: 'trusted-session',
    expiresAt: DateTime.now().toUtc().add(const Duration(minutes: 10)),
    deviceId: 'device-1',
  );

  test('starts pairing without sending credentials in the URL', () async {
    late http.Request captured;
    final client = MockClient((request) async {
      captured = request;
      return http.Response(jsonEncode({
        'request_id': 'request-opaque',
        'pairing_code': '123456',
        'pairing_secret': 'one-time-secret',
        'expires_at': DateTime.now().toUtc().add(const Duration(minutes: 5)).toIso8601String(),
        'qr_payload': 'neonshield://pair?request_id=request-opaque&secret=one-time-secret',
      }), 201);
    });
    final api = HttpsAuthApi(baseUri: Uri.parse('https://example.invalid'), client: client);
    final result = await api.startPairing(
      identity: 'owner@example.test',
      credential: 'correct-password',
      deviceId: 'new-device',
      deviceName: 'My tablet',
    );
    expect(captured.method, 'POST');
    expect(captured.url.path, '/v1/device-pairing/start');
    expect(captured.url.query, isEmpty);
    expect(jsonDecode(captured.body)['credential'], 'correct-password');
    expect(result.code, '123456');
    expect(result.requestId, 'request-opaque');
  });

  test('polls pairing status using a POST body', () async {
    late http.Request captured;
    final client = MockClient((request) async {
      captured = request;
      return http.Response(jsonEncode({'status': 'approved'}), 200);
    });
    final api = HttpsAuthApi(baseUri: Uri.parse('https://example.invalid'), client: client);
    expect(await api.pairingStatus(requestId: 'request-1', secret: 'secret-1'), 'approved');
    expect(captured.method, 'POST');
    expect(captured.url.path, '/v1/device-pairing/status');
    expect(jsonDecode(captured.body), {'request_id': 'request-1', 'pairing_secret': 'secret-1'});
  });

  test('approves a pairing request with the current trusted session', () async {
    late http.Request captured;
    final client = MockClient((request) async {
      captured = request;
      return http.Response(jsonEncode({'status': 'approved'}), 200);
    });
    final api = HttpsAuthApi(baseUri: Uri.parse('https://example.invalid'), client: client);
    await api.approvePairing(session: session, requestId: 'request-1', code: '654321');
    expect(captured.headers['authorization'], 'Bearer trusted-session');
    expect(jsonDecode(captured.body), {'request_id': 'request-1', 'pairing_code': '654321'});
  });

  test('lists, renames, and unlinks devices through authenticated endpoints', () async {
    final requests = <http.Request>[];
    final client = MockClient((request) async {
      requests.add(request);
      if (request.method == 'GET') {
        return http.Response(jsonEncode({'devices': [{
          'device_ref': '0123456789abcdef01234567',
          'device_name': 'My iPad',
          'added_at': DateTime.now().toUtc().toIso8601String(),
        }]}), 200);
      }
      return http.Response('', request.method == 'DELETE' ? 204 : 200);
    });
    final api = HttpsAuthApi(baseUri: Uri.parse('https://example.invalid'), client: client);
    final devices = await api.listDevices(session);
    expect(devices.single.name, 'My iPad');
    await api.renameDevice(session: session, deviceReference: devices.single.reference, deviceName: 'ILLUMYX iPad');
    await api.unlinkDevice(session: session, deviceReference: devices.single.reference);
    expect(requests.map((request) => request.method), ['GET', 'PATCH', 'DELETE']);
    expect(requests.every((request) => request.headers['authorization'] == 'Bearer trusted-session'), isTrue);
  });
}
