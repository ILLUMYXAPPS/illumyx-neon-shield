import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:illumyx_neon_shield/protection/protection_profile_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('defaults to the music and audio profile', () async {
    final service = ProtectionProfileService();

    final profile = await service.loadSelected();

    expect(profile.key, 'music_audio');
  });

  test('persists the selected profile across service instances', () async {
    final service = ProtectionProfileService();

    await service.select('documents');

    final reloaded = await ProtectionProfileService().loadSelected();
    expect(reloaded.key, 'documents');
  });

  test('rejects an unknown profile without replacing the saved selection', () async {
    final service = ProtectionProfileService();
    await service.select('images');

    await expectLater(service.select('not-a-real-profile'), throwsArgumentError);

    final reloaded = await ProtectionProfileService().loadSelected();
    expect(reloaded.key, 'images');
  });

  test('falls back safely when stored profile key is unknown', () async {
    SharedPreferences.setMockInitialValues({
      'neon_shield.protection_profile': 'unknown-profile',
    });

    final profile = await ProtectionProfileService().loadSelected();

    expect(profile.key, 'music_audio');
  });
}
