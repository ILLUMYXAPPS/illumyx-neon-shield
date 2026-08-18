import 'access_blocklist.dart';

/// Central access decision shared by all trusted-device authentication paths.
///
/// The backend should construct this policy from its authoritative registry of
/// exactly three trusted device IDs. Device IDs must be generated and stored by
/// the authentication service, not inferred from a phone number.
class TrustedDeviceAccessPolicy {
  TrustedDeviceAccessPolicy(Iterable<String> trustedDeviceIds)
      : _trustedDeviceIds = Set.unmodifiable(
          trustedDeviceIds.where((id) => id.trim().isNotEmpty),
        ) {
    if (_trustedDeviceIds.length > 3) {
      throw ArgumentError('Neon Shield supports at most three trusted devices.');
    }
  }

  final Set<String> _trustedDeviceIds;

  int get trustedDeviceCount => _trustedDeviceIds.length;

  bool isTrustedDevice(String deviceId) =>
      _trustedDeviceIds.contains(deviceId.trim());

  /// Returns true only when both conditions are satisfied:
  /// 1. the device is one of the registered trusted devices; and
  /// 2. the supplied phone identity is not on the denylist.
  ///
  /// This method must run before a session/token is issued. A UI-only check is
  /// not sufficient because a modified client could bypass it.
  bool canAuthorize({
    required String deviceId,
    required String phoneNumber,
  }) {
    if (!isTrustedDevice(deviceId)) return false;
    if (AccessBlocklist.isBlockedPhone(phoneNumber)) return false;
    return true;
  }
}
