import 'package:flutter_test/flutter_test.dart';
import 'package:illumyx_neon_shield/auth/auth_api_contract.dart';
import 'package:illumyx_neon_shield/auth/auth_service.dart';
import 'package:illumyx_neon_shield/auth/auth_session.dart';

class FakeAuthApi implements AuthApiContract {
  FakeAuthApi({this.trusted = true, this.failRevoke = false});

  bool trusted;
  bool failRevoke;
  int signInCalls = 0;
  int refreshCalls = 0;
  int revokeCalls = 0;
  int trustChecks = 0;

  AuthSession _session(String token, {Duration ttl = const Duration(minutes: 10)}) => AuthSession(
        token: token,
        expiresAt: DateTime.now().toUtc().add(ttl),
        deviceId: 'device-1',
      );

  @override
  Future<AuthSession> signIn({
    required String identity,
    required String credential,
    required String deviceId,
  }) async {
    signInCalls++;
    return _session('server-sign-in-token');
  }

  @override
  Future<AuthSession> refresh(AuthSession session) async {
    refreshCalls++;
    return _session('server-refresh-token');
  }

  @override
  Future<void> revoke(AuthSession session) async {
    revokeCalls++;
    if (failRevoke) throw StateError('server unavailable');
  }

  @override
  Future<bool> isDeviceTrusted(AuthSession session) async {
    trustChecks++;
    return trusted;
  }
}

class FakeStore implements AuthSessionStore {
  AuthSession? session;
  int writes = 0;
  int clears = 0;

  @override
  Future<AuthSession?> read() async => session;

  @override
  Future<void> write(AuthSession value) async {
    session = value;
    writes++;
  }

  @override
  Future<void> clear() async {
    session = null;
    clears++;
  }
}

AuthSession liveSession() => AuthSession(
      token: 'stored-token',
      expiresAt: DateTime.now().toUtc().add(const Duration(minutes: 5)),
      deviceId: 'device-1',
    );

void main() {
  test('sign-in asks the server for a session and persists it', () async {
    final api = FakeAuthApi();
    final store = FakeStore();
    final service = ServerBackedAuthService(api: api, store: store);

    final session = await service.signIn(
      identity: 'user@example.test',
      credential: 'credential',
      deviceId: 'device-1',
    );

    expect(session.token, 'server-sign-in-token');
    expect(store.session, same(session));
    expect(api.signInCalls, 1);
    expect(api.trustChecks, 1);
    expect(store.writes, 1);
  });

  test('untrusted sign-in is rejected and never persisted', () async {
    final api = FakeAuthApi(trusted: false);
    final store = FakeStore();
    final service = ServerBackedAuthService(api: api, store: store);

    await expectLater(
      service.signIn(
        identity: 'user@example.test',
        credential: 'credential',
        deviceId: 'unknown-device',
      ),
      throwsA(
        isA<AuthServiceException>().having(
          (error) => error.failure,
          'failure',
          AuthFailure.untrustedDevice,
        ),
      ),
    );

    expect(store.session, isNull);
    expect(store.writes, 0);
    expect(store.clears, 1);
  });

  test('refresh rotates the stored server session', () async {
    final api = FakeAuthApi();
    final store = FakeStore()..session = liveSession();
    final service = ServerBackedAuthService(api: api, store: store);

    final refreshed = await service.refreshSession();

    expect(refreshed?.token, 'server-refresh-token');
    expect(store.session?.token, 'server-refresh-token');
    expect(api.refreshCalls, 1);
    expect(api.trustChecks, 1);
    expect(store.writes, 1);
  });

  test('refresh refuses an expired local session before calling the server', () async {
    final api = FakeAuthApi();
    final store = FakeStore()
      ..session = AuthSession(
        token: 'expired-token',
        expiresAt: DateTime.now().toUtc().subtract(const Duration(seconds: 1)),
        deviceId: 'device-1',
      );
    final service = ServerBackedAuthService(api: api, store: store);

    expect(await service.refreshSession(), isNull);
    expect(api.refreshCalls, 0);
    expect(store.session, isNull);
    expect(store.clears, 1);
  });

  test('refresh rejects a device that is no longer trusted', () async {
    final api = FakeAuthApi(trusted: false);
    final store = FakeStore()..session = liveSession();
    final service = ServerBackedAuthService(api: api, store: store);

    await expectLater(
      service.refreshSession(),
      throwsA(
        isA<AuthServiceException>().having(
          (error) => error.failure,
          'failure',
          AuthFailure.untrustedDevice,
        ),
      ),
    );

    expect(store.session, isNull);
    expect(store.clears, 1);
  });

  test('sign-out clears local credentials even when remote revoke fails', () async {
    final api = FakeAuthApi(failRevoke: true);
    final store = FakeStore()..session = liveSession();
    final service = ServerBackedAuthService(api: api, store: store);

    await expectLater(service.signOut(store.session!), throwsStateError);

    expect(api.revokeCalls, 1);
    expect(store.session, isNull);
    expect(store.clears, 1);
  });

  test('restore requires a live server-authorized trusted session', () async {
    final api = FakeAuthApi();
    final store = FakeStore()..session = liveSession();
    final service = ServerBackedAuthService(api: api, store: store);

    final restored = await service.restoreSession();

    expect(restored?.token, 'stored-token');
    expect(api.trustChecks, 1);
    expect(store.clears, 0);
  });

  test('restore clears an expired local session without server authorization', () async {
    final api = FakeAuthApi();
    final store = FakeStore()
      ..session = AuthSession(
        token: 'expired-token',
        expiresAt: DateTime.now().toUtc().subtract(const Duration(seconds: 1)),
        deviceId: 'device-1',
      );
    final service = ServerBackedAuthService(api: api, store: store);

    expect(await service.restoreSession(), isNull);
    expect(api.trustChecks, 0);
    expect(store.session, isNull);
    expect(store.clears, 1);
  });

  test('restore clears a session when the server no longer trusts the device', () async {
    final api = FakeAuthApi(trusted: false);
    final store = FakeStore()..session = liveSession();
    final service = ServerBackedAuthService(api: api, store: store);

    expect(await service.restoreSession(), isNull);
    expect(api.trustChecks, 1);
    expect(store.session, isNull);
    expect(store.clears, 1);
  });
}
