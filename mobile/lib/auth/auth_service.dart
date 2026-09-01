import 'auth_api_contract.dart';
import 'auth_session.dart';

/// Orchestrates the mobile auth lifecycle against the server contract.
///
/// The transport is deliberately injected. This keeps the mobile layer
/// testable while allowing the production app to bind the contract to an
/// HTTPS backend without making local persistence an authority.
class ServerBackedAuthService implements AuthService {
  ServerBackedAuthService({
    required AuthApiContract api,
    required AuthSessionStore store,
  })  : _api = api,
        _store = store;

  final AuthApiContract _api;
  final AuthSessionStore _store;

  @override
  Future<AuthSession> signIn({
    required String identity,
    required String credential,
    required String deviceId,
  }) async {
    final session = await _api.signIn(
      identity: identity,
      credential: credential,
      deviceId: deviceId,
    );

    final trusted = await _api.isDeviceTrusted(session);
    if (!trusted) {
      await _store.clear();
      throw const AuthServiceException(AuthFailure.untrustedDevice);
    }

    await _store.write(session);
    return session;
  }

  /// Refreshes the currently persisted session through the server.
  Future<AuthSession?> refreshSession() async {
    final current = await _store.read();
    if (current == null || current.isExpired) {
      await _store.clear();
      return null;
    }

    final refreshed = await _api.refresh(current);
    final trusted = await _api.isDeviceTrusted(refreshed);
    if (!trusted) {
      await _store.clear();
      throw const AuthServiceException(AuthFailure.untrustedDevice);
    }

    await _store.write(refreshed);
    return refreshed;
  }

  @override
  Future<void> signOut(AuthSession session) async {
    try {
      await _api.revoke(session);
    } finally {
      // Local credentials are removed even if the server is temporarily
      // unavailable. A stale local token must never be used as proof of auth.
      await _store.clear();
    }
  }

  @override
  Future<AuthSession?> restoreSession() async {
    final session = await _store.read();
    if (session == null || session.isExpired) {
      await _store.clear();
      return null;
    }

    final trusted = await _api.isDeviceTrusted(session);
    if (!trusted) {
      await _store.clear();
      return null;
    }

    return session;
  }
}
