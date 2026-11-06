import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:illumyx_neon_shield/settings/settings_migration_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  test('first schema marker preserves existing customer preferences', () async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'neon_shield.protection_clipboard.enabled': false,
      'neon_shield.protection_clipboard.control.device_security': false,
      'neon_shield.protection_profile': 'quiet',
      'neon_shield.onboarding_complete': true,
      'customer.custom.future_setting': 'keep-me',
    });

    final version = await SettingsMigrationService().migrate();
    final preferences = await SharedPreferences.getInstance();

    expect(version, SettingsMigrationService.currentSchemaVersion);
    expect(preferences.getInt(SettingsMigrationService.schemaVersionKey), 1);
    expect(preferences.getBool('neon_shield.protection_clipboard.enabled'), isFalse);
    expect(preferences.getBool('neon_shield.protection_clipboard.control.device_security'), isFalse);
    expect(preferences.getString('neon_shield.protection_profile'), 'quiet');
    expect(preferences.getBool('neon_shield.onboarding_complete'), isTrue);
    expect(preferences.getString('customer.custom.future_setting'), 'keep-me');
  });

  test('migration copies legacy values and preserves unrelated preferences', () async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'legacy.alerts_enabled': false,
      'neon_shield.protection_profile': 'balanced',
      'unrelated.setting': 'untouched',
    });

    final service = SettingsMigrationService(migrations: [
      SettingsMigration(
        fromVersion: 0,
        toVersion: 1,
        migrate: (preferences) async {
          final legacy = preferences.getBool('legacy.alerts_enabled');
          if (legacy != null) {
            await preferences.setBool('neon_shield.security_notifications', legacy);
            if (preferences.getBool('neon_shield.security_notifications') != legacy) {
              throw StateError('Copied setting could not be verified.');
            }
            await preferences.remove('legacy.alerts_enabled');
          }
        },
      ),
    ]);

    await service.migrate();
    final preferences = await SharedPreferences.getInstance();
    expect(preferences.getBool('neon_shield.security_notifications'), isFalse);
    expect(preferences.containsKey('legacy.alerts_enabled'), isFalse);
    expect(preferences.getString('neon_shield.protection_profile'), 'balanced');
    expect(preferences.getString('unrelated.setting'), 'untouched');
  });

  test('successful migrations run only once', () async {
    var calls = 0;
    final service = SettingsMigrationService(migrations: [
      SettingsMigration(fromVersion: 0, toVersion: 1, migrate: (_) async { calls++; }),
    ]);

    await service.migrate();
    await service.migrate();
    expect(calls, 1);
  });

  test('failed migration rolls back changed settings and version', () async {
    SharedPreferences.setMockInitialValues(<String, Object>{'customer.preference': false});
    final service = SettingsMigrationService(migrations: [
      SettingsMigration(
        fromVersion: 0,
        toVersion: 1,
        migrate: (preferences) async {
          await preferences.setBool('customer.preference', true);
          await preferences.setString('partial.new_key', 'partial');
          throw StateError('Simulated migration failure');
        },
      ),
    ]);

    await expectLater(service.migrate(), throwsStateError);
    final preferences = await SharedPreferences.getInstance();
    expect(preferences.getBool('customer.preference'), isFalse);
    expect(preferences.containsKey('partial.new_key'), isFalse);
    expect(preferences.getInt(SettingsMigrationService.schemaVersionKey), isNull);
  });

  test('refuses to downgrade settings written by a newer app', () async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      SettingsMigrationService.schemaVersionKey: 99,
      'customer.preference': false,
    });

    await expectLater(SettingsMigrationService().migrate(), throwsStateError);
    final preferences = await SharedPreferences.getInstance();
    expect(preferences.getInt(SettingsMigrationService.schemaVersionKey), 99);
    expect(preferences.getBool('customer.preference'), isFalse);
  });
}
