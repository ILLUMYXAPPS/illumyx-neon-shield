import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:illumyx_neon_shield/protection/protection_clipboard_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('clipboard and all six customer choices default to disabled', () async {
    final service = ProtectionClipboardService();

    expect(await service.loadEnabled(), isFalse);
    final controls = await service.loadControls();
    expect(controls, hasLength(6));
    expect(controls.values, everyElement(isFalse));
  });

  test('master ON/OFF choice persists across service instances', () async {
    final service = ProtectionClipboardService();

    await service.setEnabled(false);
    expect(await ProtectionClipboardService().loadEnabled(), isFalse);

    await service.setEnabled(true);
    expect(await ProtectionClipboardService().loadEnabled(), isTrue);
  });

  test('each protection choice persists independently', () async {
    final service = ProtectionClipboardService();

    await service.setControlEnabled('device_security', false);
    await service.setControlEnabled('network_safety', false);

    final controls = await ProtectionClipboardService().loadControls();
    expect(controls['device_security'], isFalse);
    expect(controls['network_safety'], isFalse);
    expect(controls['privacy_protection'], isFalse);
    expect(controls['app_monitoring'], isFalse);
    expect(controls['family_safety'], isFalse);
    expect(controls['security_notifications'], isFalse);
  });

  test('rejects unknown control keys', () async {
    final service = ProtectionClipboardService();

    await expectLater(
      service.setControlEnabled('unknown_control', false),
      throwsArgumentError,
    );
  });
}
