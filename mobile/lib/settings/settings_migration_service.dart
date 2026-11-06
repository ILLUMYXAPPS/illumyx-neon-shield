import 'package:shared_preferences/shared_preferences.dart';

/// An ordered, one-version-at-a-time upgrade for customer preferences.
/// Migrations should copy and verify values before removing legacy keys.
class SettingsMigration {
  const SettingsMigration({
    required this.fromVersion,
    required this.toVersion,
    required this.migrate,
  });

  final int fromVersion;
  final int toVersion;
  final Future<void> Function(SharedPreferences preferences) migrate;
}

/// Runs before app screens read preferences. Unknown keys are retained so
/// feature-owned and future settings are not discarded by older migrations.
class SettingsMigrationService {
  SettingsMigrationService({List<SettingsMigration>? migrations})
      : _migrations = migrations ?? _defaultMigrations;

  static const schemaVersionKey = 'neon_shield.settings_schema_version';
  static const currentSchemaVersion = 1;

  static final List<SettingsMigration> _defaultMigrations = [
    // V1 establishes an explicit schema marker. Existing keys are already
    // namespaced, so this initial migration deliberately leaves them untouched.
    SettingsMigration(fromVersion: 0, toVersion: 1, migrate: (_) async {}),
  ];

  final List<SettingsMigration> _migrations;

  Future<int> migrate() async {
    final preferences = await SharedPreferences.getInstance();
    var version = preferences.getInt(schemaVersionKey) ?? 0;

    if (version > currentSchemaVersion) {
      throw StateError(
        'Settings were written by a newer Neon Shield version. '
        'Refusing to downgrade or overwrite customer preferences.',
      );
    }

    while (version < currentSchemaVersion) {
      final candidates = _migrations.where((item) => item.fromVersion == version);
      if (candidates.length != 1) {
        throw StateError('No unique settings migration exists from version $version.');
      }
      final migration = candidates.single;
      if (migration.toVersion != version + 1) {
        throw StateError('Settings migrations must advance exactly one version.');
      }

      final before = _snapshot(preferences);
      try {
        await migration.migrate(preferences);
        await preferences.setInt(schemaVersionKey, migration.toVersion);
        version = migration.toVersion;
      } catch (_) {
        await _restore(preferences, before);
        rethrow;
      }
    }
    return version;
  }

  Map<String, Object> _snapshot(SharedPreferences preferences) => {
        for (final key in preferences.getKeys())
          if (preferences.get(key) != null) key: preferences.get(key)!,
      };

  Future<void> _restore(
    SharedPreferences preferences,
    Map<String, Object> before,
  ) async {
    final currentKeys = preferences.getKeys();
    for (final key in currentKeys.difference(before.keys.toSet())) {
      await preferences.remove(key);
    }
    for (final entry in before.entries) {
      await _writeValue(preferences, entry.key, entry.value);
    }
  }

  Future<void> _writeValue(
    SharedPreferences preferences,
    String key,
    Object value,
  ) async {
    if (value is bool) {
      await preferences.setBool(key, value);
    } else if (value is int) {
      await preferences.setInt(key, value);
    } else if (value is double) {
      await preferences.setDouble(key, value);
    } else if (value is String) {
      await preferences.setString(key, value);
    } else if (value is List<String>) {
      await preferences.setStringList(key, value);
    } else {
      throw StateError('Unsupported preference value for key $key.');
    }
  }
}
