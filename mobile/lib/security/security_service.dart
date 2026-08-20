import 'dart:math';

class SecuritySnapshot {
  const SecuritySnapshot({
    required this.ownerInitialized,
    required this.trustedDeviceCount,
  });

  final bool ownerInitialized;
  final int trustedDeviceCount;
}

/// Mobile application boundary for security state.
///
/// The mobile UI depends on this Dart service rather than importing the
/// repository's Python policy implementation directly.
class SecurityService {
  bool _ownerInitialized = false;
  final Set<String> _trustedDevices = <String>{};

  SecuritySnapshot snapshot() => SecuritySnapshot(
        ownerInitialized: _ownerInitialized,
        trustedDeviceCount: _trustedDevices.length,
      );

  void initializeOwner() {
    if (_ownerInitialized) {
      throw StateError('Ownership is already initialized');
    }
    _ownerInitialized = true;
  }

  void addTrustedDevice(String deviceId) {
    if (!_ownerInitialized) {
      throw StateError('Owner initialization is required');
    }
    if (deviceId.trim().isEmpty) {
      throw ArgumentError.value(deviceId, 'deviceId', 'must not be empty');
    }
    _trustedDevices.add(deviceId);
  }

  void removeTrustedDevice(String deviceId) {
    if (!_ownerInitialized) {
      throw StateError('Owner initialization is required');
    }
    _trustedDevices.remove(deviceId);
  }

  bool isTrustedDevice(String deviceId) => _trustedDevices.contains(deviceId);

  String generateBootstrapIdentifier() {
    final random = Random.secure();
    final bytes = List<int>.generate(24, (_) => random.nextInt(256));
    return bytes.map((byte) => byte.toRadixString(16).padLeft(2, '0')).join();
  }
}
