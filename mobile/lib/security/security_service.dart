import 'dart:math';

import 'package:shared_preferences/shared_preferences.dart';

import 'access_blocklist.dart';

class SecuritySnapshot {
  const SecuritySnapshot({
    required this.ownerInitialized,
    required this.trustedDeviceCount,
  });

  final bool ownerInitialized;
  final int trustedDeviceCount;
}

/// Mobile application boundary for persisted security state.
///
/// The mobile UI depends on this Dart service rather than importing the
/// repository's Python policy implementation directly.
class SecurityService {
  static const String _ownerKey = 'neon_shield.owner_initialized';
  static const String _trustedDevicesKey = 'neon_shield.trusted_devices';

  bool _ownerInitialized = false;
  final Set<String> _trustedDevices = <String>{};
  bool _loaded = false;

  SecuritySnapshot snapshot() => SecuritySnapshot(
        ownerInitialized: _ownerInitialized,
        trustedDeviceCount: _trustedDevices.length,
      );

  bool get isLoaded => _loaded;

  Future<void> load() async {
    final preferences = await SharedPreferences.getInstance();
    _ownerInitialized = preferences.getBool(_ownerKey) ?? false;
    _trustedDevices
      ..clear()
      ..addAll(preferences.getStringList(_trustedDevicesKey) ?? const <String>[]);
    _loaded = true;
  }

  Future<void> initializeOwner() async {
    _requireLoaded();
    if (_ownerInitialized) {
      throw StateError('Ownership is already initialized');
    }
    final preferences = await SharedPreferences.getInstance();
    await preferences.setBool(_ownerKey, true);
    _ownerInitialized = true;
  }

  Future<void> addTrustedDevice(String deviceId) async {
    _requireLoaded();
    if (!_ownerInitialized) {
      throw StateError('Owner initialization is required');
    }
    final normalizedId = deviceId.trim();
    if (normalizedId.isEmpty) {
      throw ArgumentError.value(deviceId, 'deviceId', 'must not be empty');
    }
    if (_trustedDevices.add(normalizedId)) {
      await _persistTrustedDevices();
    }
  }

  Future<void> removeTrustedDevice(String deviceId) async {
    _requireLoaded();
    if (!_ownerInitialized) {
      throw StateError('Owner initialization is required');
    }
    final normalizedId = deviceId.trim();
    if (_trustedDevices.remove(normalizedId)) {
      await _persistTrustedDevices();
    }
  }

  bool isTrustedDevice(String deviceId) =>
      _trustedDevices.contains(deviceId.trim());

  /// Returns true only when the persisted security state is loaded, ownership
  /// is initialized, the device is trusted, and the supplied phone identity
  /// is a non-empty normalized value that is not on the privacy-preserving
  /// denylist.
  ///
  /// This is the final client-side access decision available to the current
  /// beta. A real authentication/backend service must repeat the same policy
  /// before issuing a session or token because a modified client can bypass
  /// client-side checks.
  bool canAuthorize({
    required String deviceId,
    required String phoneNumber,
  }) {
    if (!_loaded || !_ownerInitialized) return false;
    if (!isTrustedDevice(deviceId)) return false;
    final normalizedPhone = AccessBlocklist.normalizePhone(phoneNumber);
    if (normalizedPhone.isEmpty) return false;
    if (AccessBlocklist.isBlockedPhone(normalizedPhone)) return false;
    return true;
  }

  String generateBootstrapIdentifier() {
    final random = Random.secure();
    final bytes = List<int>.generate(24, (_) => random.nextInt(256));
    return bytes.map((byte) => byte.toRadixString(16).padLeft(2, '0')).join();
  }

  void _requireLoaded() {
    if (!_loaded) {
      throw StateError('Security state must be loaded before use');
    }
  }

  Future<void> _persistTrustedDevices() async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setStringList(
      _trustedDevicesKey,
      _trustedDevices.toList()..sort(),
    );
  }
}
