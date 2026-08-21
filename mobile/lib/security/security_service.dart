import 'dart:convert';
import 'dart:math';

import 'package:shared_preferences/shared_preferences.dart';

import 'access_blocklist.dart';

class SecuritySnapshot {
  const SecuritySnapshot({
    required this.ownerInitialized,
    required this.trustedDeviceCount,
    required this.securityEventCount,
  });

  final bool ownerInitialized;
  final int trustedDeviceCount;
  final int securityEventCount;
}

class SecurityEvent {
  const SecurityEvent({
    required this.type,
    required this.deviceId,
    required this.reason,
    required this.timestamp,
  });

  final String type;
  final String deviceId;
  final String reason;
  final DateTime timestamp;

  Map<String, Object> toJson() => <String, Object>{
        'type': type,
        'deviceId': deviceId,
        'reason': reason,
        'timestamp': timestamp.toUtc().toIso8601String(),
      };

  static SecurityEvent fromJson(Map<String, dynamic> json) => SecurityEvent(
        type: json['type'] as String? ?? 'unknown',
        deviceId: json['deviceId'] as String? ?? '',
        reason: json['reason'] as String? ?? '',
        timestamp: DateTime.tryParse(json['timestamp'] as String? ?? '') ??
            DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      );
}

/// Mobile application boundary for persisted security state.
///
/// The mobile UI depends on this Dart service rather than importing the
/// repository's Python policy implementation directly.
class SecurityService {
  static const String _ownerKey = 'neon_shield.owner_initialized';
  static const String _trustedDevicesKey = 'neon_shield.trusted_devices';
  static const String _securityEventsKey = 'neon_shield.security_events';

  bool _ownerInitialized = false;
  final Set<String> _trustedDevices = <String>{};
  final List<SecurityEvent> _securityEvents = <SecurityEvent>[];
  bool _loaded = false;

  SecuritySnapshot snapshot() => SecuritySnapshot(
        ownerInitialized: _ownerInitialized,
        trustedDeviceCount: _trustedDevices.length,
        securityEventCount: _securityEvents.length,
      );

  List<SecurityEvent> get recentSecurityEvents =>
      List<SecurityEvent>.unmodifiable(_securityEvents.reversed);

  bool get isLoaded => _loaded;

  Future<void> load() async {
    final preferences = await SharedPreferences.getInstance();
    _ownerInitialized = preferences.getBool(_ownerKey) ?? false;
    _trustedDevices
      ..clear()
      ..addAll(preferences.getStringList(_trustedDevicesKey) ?? const <String>[]);
    _securityEvents
      ..clear()
      ..addAll(
        (preferences.getStringList(_securityEventsKey) ?? const <String>[])
            .map((entry) => SecurityEvent.fromJson(
                  jsonDecode(entry) as Map<String, dynamic>,
                )),
      );
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

  /// Records an unsupported-device attempt without granting access.
  ///
  /// A production backend must enforce the same decision server-side before
  /// issuing a session or token. The mobile record is an audit aid, not an
  /// authentication boundary.
  Future<void> recordUnsupportedLogin({
    required String deviceId,
    String reason = 'unrecognised device',
  }) async {
    _requireLoaded();
    final normalizedId = deviceId.trim();
    final event = SecurityEvent(
      type: 'unsupported_login',
      deviceId: normalizedId,
      reason: reason,
      timestamp: DateTime.now().toUtc(),
    );
    _securityEvents.add(event);
    if (_securityEvents.length > 100) {
      _securityEvents.removeRange(0, _securityEvents.length - 100);
    }
    await _persistSecurityEvents();
  }

  /// Returns true only when the persisted security state is loaded, ownership
  /// is initialized, the device is trusted, and the supplied phone identity
  /// is a non-empty normalized value that is not on the privacy-preserving
  /// denylist.
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

  Future<void> _persistSecurityEvents() async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setStringList(
      _securityEventsKey,
      _securityEvents.map((event) => jsonEncode(event.toJson())).toList(),
    );
  }
}
