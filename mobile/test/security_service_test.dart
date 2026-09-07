import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:illumyx_neon_shield/security/security_service.dart';

class FakeTrustedDeviceStore implements TrustedDeviceStore {
  FakeTrustedDeviceStore([List<String>? initial])
      : devices = initial == null ? null : List<String>.from(initial);

  List<String>? devices;
  bool failWrites = false;
  int writeCount = 0;

  @override
  Future<List<String>?> readTrustedDevices() async =>
      devices == null ? null : List<String>.from(devices!);

  @override
  Future<void> writeTrustedDevices(List<String> deviceIds) async {
    writeCount++;
    if (failWrites) throw StateError('secure storage write failed');
    devices = List<String>.from(deviceIds);
  }
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  test('persists owner initialization and trusted devices', () async {
    final store = FakeTrustedDeviceStore();
    final first = SecurityService(trustedDeviceStore: store);
    await first.load();

    expect(first.snapshot().ownerInitialized, isFalse);
    expect(first.snapshot().trustedDeviceCount, 0);

    await first.initializeOwner();
    await first.addTrustedDevice('device-a');
    await first.addTrustedDevice('device-b');

    final restored = SecurityService(trustedDeviceStore: store);
    await restored.load();

    expect(restored.snapshot().ownerInitialized, isTrue);
    expect(restored.snapshot().trustedDeviceCount, 2);
    expect(restored.isTrustedDevice('device-a'), isTrue);
    expect(restored.isTrustedDevice('device-b'), isTrue);
  });

  test('does not allow ownership to be initialized twice', () async {
    final service = SecurityService(trustedDeviceStore: FakeTrustedDeviceStore());
    await service.load();
    await service.initializeOwner();

    await expectLater(service.initializeOwner(), throwsA(isA<StateError>()));
  });

  test('requires owner initialization before adding a device', () async {
    final service = SecurityService(trustedDeviceStore: FakeTrustedDeviceStore());
    await service.load();

    await expectLater(
      service.addTrustedDevice('device-a'),
      throwsA(isA<StateError>()),
    );
  });

  test('rejects empty trusted device identifiers', () async {
    final service = SecurityService(trustedDeviceStore: FakeTrustedDeviceStore());
    await service.load();
    await service.initializeOwner();

    await expectLater(
      service.addTrustedDevice('   '),
      throwsA(isA<ArgumentError>()),
    );
  });

  test('normalizes trusted device identifiers when removing', () async {
    final store = FakeTrustedDeviceStore();
    final service = SecurityService(trustedDeviceStore: store);
    await service.load();
    await service.initializeOwner();
    await service.addTrustedDevice('device-a');

    await service.removeTrustedDevice('  device-a  ');

    expect(service.snapshot().trustedDeviceCount, 0);
    expect(service.isTrustedDevice('device-a'), isFalse);
    expect(store.devices, isEmpty);
  });

  test('canonicalizes malformed persisted trusted-device entries', () async {
    final store = FakeTrustedDeviceStore(<String>[
      ' device-a ',
      '',
      '   ',
      'device-a',
      'device-b ',
    ]);
    SharedPreferences.setMockInitialValues(<String, Object>{
      'neon_shield.owner_initialized': true,
    });

    final service = SecurityService(trustedDeviceStore: store);
    await service.load();

    expect(service.snapshot().ownerInitialized, isTrue);
    expect(service.snapshot().trustedDeviceCount, 2);
    expect(service.isTrustedDevice('device-a'), isTrue);
    expect(service.isTrustedDevice(' device-a '), isTrue);
    expect(service.isTrustedDevice('device-b'), isTrue);
    expect(service.isTrustedDevice(''), isFalse);
  });

  test('does not create duplicate trusted-device state', () async {
    final store = FakeTrustedDeviceStore();
    final service = SecurityService(trustedDeviceStore: store);
    await service.load();
    await service.initializeOwner();

    await service.addTrustedDevice('device-a');
    await service.addTrustedDevice('  device-a  ');

    expect(service.snapshot().trustedDeviceCount, 1);
    expect(store.writeCount, 1);
  });

  test('rolls back a newly trusted device when secure persistence fails', () async {
    final store = FakeTrustedDeviceStore()..failWrites = true;
    final service = SecurityService(trustedDeviceStore: store);
    await service.load();
    await service.initializeOwner();

    await expectLater(
      service.addTrustedDevice('device-a'),
      throwsA(isA<StateError>()),
    );
    expect(service.snapshot().trustedDeviceCount, 0);
    expect(service.isTrustedDevice('device-a'), isFalse);
  });

  test('restores a removed trusted device when secure persistence fails', () async {
    final store = FakeTrustedDeviceStore(<String>['device-a'])
      ..failWrites = true;
    final service = SecurityService(trustedDeviceStore: store);
    await service.load();
    await service.initializeOwner();

    await expectLater(
      service.removeTrustedDevice('device-a'),
      throwsA(isA<StateError>()),
    );
    expect(service.snapshot().trustedDeviceCount, 1);
    expect(service.isTrustedDevice('device-a'), isTrue);
  });

  test('does not trust devices from the legacy SharedPreferences store', () async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'neon_shield.owner_initialized': true,
      'neon_shield.trusted_devices': <String>['legacy-device'],
    });

    final service = SecurityService(trustedDeviceStore: FakeTrustedDeviceStore());
    await service.load();

    expect(service.snapshot().trustedDeviceCount, 0);
    expect(service.isTrustedDevice('legacy-device'), isFalse);
  });

  test('denies authorization until persisted security state is loaded', () {
    final service = SecurityService(trustedDeviceStore: FakeTrustedDeviceStore());

    expect(
      service.canAuthorize(
        deviceId: 'device-a',
        phoneNumber: '0400000000',
      ),
      isFalse,
    );
  });

  test('allows an initialized trusted device with an unblocked identity', () async {
    final service = SecurityService(trustedDeviceStore: FakeTrustedDeviceStore());
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

  test('denies an empty phone identity even on a trusted device', () async {
    final service = SecurityService(trustedDeviceStore: FakeTrustedDeviceStore());
    await service.load();
    await service.initializeOwner();
    await service.addTrustedDevice('device-a');

    expect(
      service.canAuthorize(
        deviceId: 'device-a',
        phoneNumber: '   ',
      ),
      isFalse,
    );
    expect(
      service.canAuthorize(
        deviceId: 'device-a',
        phoneNumber: '---',
      ),
      isFalse,
    );
  });

  test('denies a blocked phone identity even on a trusted device', () async {
    final service = SecurityService(trustedDeviceStore: FakeTrustedDeviceStore());
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
    final service = SecurityService(trustedDeviceStore: FakeTrustedDeviceStore());
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
