import 'auth_session.dart';

/// Provider-neutral contract for the future Neon Shield identity service.
///
/// Implementations must use HTTPS and treat the server as authoritative for
/// authentication, session validity, revocation, and trusted-device policy.
abstract interface class AuthApiContract {
  Future<AuthSession> signIn({
    required String identity,
    required String credential,
    required String deviceId,
  });

  Future<AuthSession> refresh(AuthSession session);

  Future<void> revoke(AuthSession session);

  Future<bool> isDeviceTrusted(AuthSession session);
}

/// Stable operation names for audit and telemetry integration.
enum AuthOperation {
  signIn,
  refresh,
  revoke,
  trustedDeviceCheck,
}

/// Explicit outcomes the client can map to safe UI states.
enum AuthFailure {
  invalidCredentials,
  expiredSession,
  revokedSession,
  untrustedDevice,
  rateLimited,
  unavailable,
}

class AuthServiceException implements Exception {
  const AuthServiceException(this.failure);

  final AuthFailure failure;

  @override
  String toString() => 'AuthServiceException(${failure.name})';
}
