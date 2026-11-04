import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:illumyx_neon_shield/companion/ad_bugsworth_settings.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('AdBugsworthSettings', () {
    late AdBugsworthSettings settings;

    setUp(() {
      SharedPreferences.setMockInitialValues({});
      settings = AdBugsworthSettings();
    });

    test('defaults to OFF for a new customer', () async {
      expect(await settings.loadEnabled(), isFalse);
    });

    test('persists ON and OFF choices', () async {
      await settings.saveEnabled(true);
      expect(await settings.loadEnabled(), isTrue);

      await settings.saveEnabled(false);
      expect(await settings.loadEnabled(), isFalse);
    });
  });
}
