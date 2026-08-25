import 'package:flutter_test/flutter_test.dart';
import 'package:illumyx_neon_shield/auth/auth_api_contract.dart';
import 'package:illumyx_neon_shield/auth/auth_service.dart';
import 'package:illumyx_neon_shield/auth/auth_session.dart';

class FakeAuthApi implements AuthApiContract {
  FakeAuthApi({this.trusted = true});

  bool trusted;
  int signInCalls = 0;
  int refreshCalls = 0;
  int revokeCalls = 0;

  AuthSession _session(String token) => AuthSession(
        token: token,
        expiresAt: DateTime.now().toUtc().add(const Duration(minutes: 10)),
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
  }

  @override
  Future<bool> isDeviceTrusted(AuthSession session) async => trusted;
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
  });

  test('refresh rotates the stored server session', () async {
    final api = FakeAuthApi();
    final store = FakeStore();
    store.session = AuthSession(
      token: 'old-token',
      expiresAt: DateTime.now().toUtc().add(const Duration(minutes: 5)),
      deviceId: 'device-1',
    );
    final service = ServerBackedAuthService(api: api, store: store);

    final refreshed = await service.refreshSession();

    expect(refreshed?.token, 'server-refresh-token');
    expect(store.session?.token, 'server-refresh-token');
    expect(api.refreshCalls, 1);
  });

  test('sign-out revokes remotely and always clears local state', () async {
    final api = FakeAuthApi();
    final store = FakeStore();
    final service = ServerBackedAuthService(api: api, store: store);
    final session = await service.signIn(
      identity: 'user@example.test',
      credential: 'credential',
      deviceId: 'device-1',
    );

    await service.signOut(session);

    expect(api.revokeCalls, 1);
    expect(store.session, isNull);
    expect(store.clears, 1);
  });

  test('restore requires a live server-authorized trusted session', () async {
    final api = FakeAuthApi();
    final store = FakeStore();
    store.session = AuthSession(
      token: 'stored-token',
      expiresAt: DateTime.now().toUtc().add(const Duration(minutes: 5)),
      deviceId: 'device-1',
    );
    final service = ServerBackedAuthService(api: api, store: store);

    final restored = await service.restoreSession();

    expect(restored?.token, 'stored-token');
    expect(store.clears, 0);
  });

  test('restore clears an expired local session', () async {
    final api = FakeAuthApi();
    final store = FakeStore();
    store.session = AuthSession(
      token: 'expired-token',
      expiresAt: DateTime.now().toUtc().subtract(const Duration(seconds: 1)),
      deviceId: 'device-1',
    );
    final service = ServerBackedAuthService(api: api, store: store);

    expect(await service.restoreSession(), isNull);
    expect(store.session, isNull);
    expect(store.clears, 1);
  });
}
