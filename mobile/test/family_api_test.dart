import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:illumyx_neon_shield/auth/auth_session.dart';
import 'package:illumyx_neon_shield/family/family_api.dart';

void main() {
  final session = AuthSession(
    token: 'family-session',
    expiresAt: DateTime.utc(2027),
    deviceId: 'device-1',
  );

  test('create invitation sends authenticated request and parses one-time code', () async {
    late http.Request request;
    final client = MockClient((incoming) async {
      request = incoming;
      return http.Response(jsonEncode({
        'invitation_id': 'invite_1234567890123456',
        'invitation_code': 'one-time-secret-code',
        'expires_at': '2026-11-15T00:00:00+00:00',
      }), 201);
    });
    final api = HttpsFamilyInvitationsApi(
      baseUri: Uri.parse('https://example.invalid'),
      client: client,
    );

    final result = await api.create(session);
    expect(request.method, 'POST');
    expect(request.url.path, '/v1/family/invitations');
    expect(request.headers['authorization'], 'Bearer family-session');
    expect(result.code, 'one-time-secret-code');
    expect(result.id, 'invite_1234567890123456');
  });

  test('lists pending invitation metadata without a secret token', () async {
    final client = MockClient((_) async => http.Response(jsonEncode({
      'invitations': [{
        'invitation_id': 'invite_1234567890123456',
        'status': 'pending',
        'created_at': '2026-11-08T00:00:00+00:00',
        'expires_at': '2026-11-15T00:00:00+00:00',
      }],
    }), 200));
    final api = HttpsFamilyInvitationsApi(
      baseUri: Uri.parse('https://example.invalid'),
      client: client,
    );

    final result = await api.list(session);
    expect(result, hasLength(1));
    expect(result.single.code, isNull);
  });

  test('accepts a code with authenticated consent request', () async {
    late http.Request request;
    final client = MockClient((incoming) async {
      request = incoming;
      return http.Response(jsonEncode({'status': 'accepted'}), 200);
    });
    final api = HttpsFamilyInvitationsApi(
      baseUri: Uri.parse('https://example.invalid'),
      client: client,
    );

    await api.accept(session, '  one-time-secret-code  ');
    expect(request.url.path, '/v1/family/invitations/accept');
    expect(jsonDecode(request.body), {'invitation_code': 'one-time-secret-code'});
    expect(request.headers['authorization'], 'Bearer family-session');
  });

  test('revokes only through authenticated owner endpoint', () async {
    late http.Request request;
    final client = MockClient((incoming) async {
      request = incoming;
      return http.Response(jsonEncode({'revoked': true}), 200);
    });
    final api = HttpsFamilyInvitationsApi(
      baseUri: Uri.parse('https://example.invalid'),
      client: client,
    );

    expect(await api.revoke(session, 'invite_1234567890123456'), isTrue);
    expect(request.method, 'DELETE');
    expect(request.url.path, '/v1/family/invitations/invite_1234567890123456');
    expect(request.headers['authorization'], 'Bearer family-session');
  });

  test('maps server Family entitlement failures to a customer message', () async {
    final client = MockClient((_) async => http.Response(
      jsonEncode({'error': 'active_premium_family_required'}),
      403,
    ));
    final api = HttpsFamilyInvitationsApi(
      baseUri: Uri.parse('https://example.invalid'),
      client: client,
    );

    await expectLater(
      api.create(session),
      throwsA(isA<FamilyApiException>().having(
        (error) => error.message,
        'message',
        contains('Premium Family'),
      )),
    );
  });
}
