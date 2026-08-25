/// Provider-agnostic server-session boundary for Neon Shield.
///
/// This layer deliberately does not implement a network client. The mobile
/// application can depend on this contract now and bind it to a production
/// identity service later without treating local state as proof of auth.
class AuthSession {
  const AuthSession({
    required this.token,
    required this.expiresAt,
    required this.deviceId,
  });

  final String token;
  final DateTime expiresAt;
  final String deviceId;

  bool get isExpired => !DateTime.now().toUtc().isBefore(expiresAt.toUtc());
}

abstract interface class AuthSessionStore {
  Future<AuthSession?> read();
  Future<void> write(AuthSession session);
  Future<void> clear();
}

abstract interface class AuthService {
  Future<AuthSession> signIn({
    required String identity,
    required String credential,
    required String deviceId,
  });

  Future<void> signOut(AuthSession session);

  Future<AuthSession?> restoreSession();
}
