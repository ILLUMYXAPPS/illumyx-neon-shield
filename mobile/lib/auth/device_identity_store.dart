import 'dart:math';

import 'secure_auth_session_store.dart';

/// Creates a stable client identifier for server-side device registration.
///
/// This identifier is only a correlation value. It is not device attestation
/// and must never be treated as proof of trust by the server.
class SecureDeviceIdentityStore {
  SecureDeviceIdentityStore({AuthSecretStorage? storage})
      : _storage = storage ?? FlutterAuthSecretStorage();

  static const _key = 'neon_shield.device_identity';
  final AuthSecretStorage _storage;

  Future<String> getOrCreate() async {
    final existing = await _storage.read(key: _key);
    if (existing != null && RegExp(r'^[a-f0-9]{64}$').hasMatch(existing)) {
      return existing;
    }

    final random = Random.secure();
    final value = List<int>.generate(32, (_) => random.nextInt(256))
        .map((byte) => byte.toRadixString(16).padLeft(2, '0'))
        .join();
    await _storage.write(key: _key, value: value);
    return value;
  }
}
