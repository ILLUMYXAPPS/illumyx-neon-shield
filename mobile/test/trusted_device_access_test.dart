import 'package:flutter_test/flutter_test.dart';
import 'package:illumyx_neon_shield/trusted_device_access.dart';

void main() {
  final policy = TrustedDeviceAccessPolicy(const [
    'trusted-device-1',
    'trusted-device-2',
    'trusted-device-3',
  ]);

  test('registers exactly three trusted devices', () {
    expect(policy.trustedDeviceCount, 3);
    expect(policy.isTrustedDevice('trusted-device-1'), isTrue);
    expect(policy.isTrustedDevice('untrusted-device'), isFalse);
  });

  test('blocks the configured phone identities on every trusted device', () {
    for (final device in const [
      'trusted-device-1',
      'trusted-device-2',
      'trusted-device-3',
    ]) {
      expect(
        policy.canAuthorize(
          deviceId: device,
          phoneNumber: '0422122753',
        ),
        isFalse,
      );
      expect(
        policy.canAuthorize(
          deviceId: device,
          phoneNumber: '0427488809',
        ),
        isFalse,
      );
    }
  });

  test('allows an unblocked identity on a trusted device', () {
    expect(
      policy.canAuthorize(
        deviceId: 'trusted-device-2',
        phoneNumber: '0400000000',
      ),
      isTrue,
    );
  });

  test('rejects an untrusted device even for an unblocked identity', () {
    expect(
      policy.canAuthorize(
        deviceId: 'unknown-device',
        phoneNumber: '0400000000',
      ),
      isFalse,
    );
  });

  test('rejects more than three trusted devices', () {
    expect(
      () => TrustedDeviceAccessPolicy(const [
        '1',
        '2',
        '3',
        '4',
      ]),
      throwsArgumentError,
    );
  });
}
