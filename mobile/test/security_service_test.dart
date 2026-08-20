import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:illumyx_neon_shield/security/security_service.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  test('persists owner initialization and trusted devices', () async {
    final first = SecurityService();
    await first.load();

    expect(first.snapshot().ownerInitialized, isFalse);
    expect(first.snapshot().trustedDeviceCount, 0);

    await first.initializeOwner();
    await first.addTrustedDevice('device-a');
    await first.addTrustedDevice('device-b');

    final restored = SecurityService();
    await restored.load();

    expect(restored.snapshot().ownerInitialized, isTrue);
    expect(restored.snapshot().trustedDeviceCount, 2);
    expect(restored.isTrustedDevice('device-a'), isTrue);
    expect(restored.isTrustedDevice('device-b'), isTrue);
  });

  test('does not allow ownership to be initialized twice', () async {
    final service = SecurityService();
    await service.load();
    await service.initializeOwner();

    await expectLater(service.initializeOwner(), throwsA(isA<StateError>()));
  });

  test('requires owner initialization before adding a device', () async {
    final service = SecurityService();
    await service.load();

    await expectLater(
      service.addTrustedDevice('device-a'),
      throwsA(isA<StateError>()),
    );
  });

  test('rejects empty trusted device identifiers', () async {
    final service = SecurityService();
    await service.load();
    await service.initializeOwner();

    await expectLater(
      service.addTrustedDevice('   '),
      throwsA(isA<ArgumentError>()),
    );
  });

  test('normalizes trusted device identifiers when removing', () async {
    final service = SecurityService();
    await service.load();
    await service.initializeOwner();
    await service.addTrustedDevice('device-a');

    await service.removeTrustedDevice('  device-a  ');

    expect(service.snapshot().trustedDeviceCount, 0);
    expect(service.isTrustedDevice('device-a'), isFalse);
  });

  test('denies authorization until persisted security state is loaded', () {
    final service = SecurityService();

    expect(
      service.canAuthorize(
        deviceId: 'device-a',
        phoneNumber: '0400000000',
      ),
      isFalse,
    );
  });

  test('allows an initialized trusted device with an unblocked identity', () async {
    final service = SecurityService();
    await service.load();
    await service.initializeOwner();
    await service.addTrustedDevice('device-a');

    expect(
      service.canAuthorize(
        deviceId: 'device-a',
        phoneNumber: '0400000000',
      ),
      isTrue,
    );
  });

  test('denies a blocked phone identity even on a trusted device', () async {
    final service = SecurityService();
    await service.load();
    await service.initializeOwner();
    await service.addTrustedDevice('device-a');

    expect(
      service.canAuthorize(
        deviceId: 'device-a',
        phoneNumber: '0422122753',
      ),
      isFalse,
    );
    expect(
      service.canAuthorize(
        deviceId: 'device-a',
        phoneNumber: '+61 427 488 809',
      ),
      isFalse,
    );
  });

  test('denies an untrusted device even with an unblocked identity', () async {
    final service = SecurityService();
    await service.load();
    await service.initializeOwner();
    await service.addTrustedDevice('device-a');

    expect(
      service.canAuthorize(
        deviceId: 'unknown-device',
        phoneNumber: '0400000000',
      ),
      isFalse,
    );
  });
}
