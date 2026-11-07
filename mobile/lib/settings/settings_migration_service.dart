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
        final versionSaved = await preferences.setInt(schemaVersionKey, migration.toVersion);
        if (!versionSaved || preferences.getInt(schemaVersionKey) != migration.toVersion) {
          throw StateError('Settings schema version could not be saved and verified.');
        }
        version = migration.toVersion;
      } catch (migrationError) {
        try {
          await _restore(preferences, before);
        } catch (restoreError) {
          throw StateError('Settings migration failed ($migrationError) and rollback could not be verified ($restoreError). Stop startup and preserve the settings for recovery.');
        }
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
      final removed = await preferences.remove(key);
      if (!removed || preferences.containsKey(key)) {
        throw StateError('Could not remove partially written preference $key during rollback.');
      }
    }
    for (final entry in before.entries) {
      await _writeValue(preferences, entry.key, entry.value);
      if (preferences.get(entry.key) != entry.value &&
          !(entry.value is List<String> && preferences.get(entry.key) is List<String> &&
            _sameStringList(preferences.get(entry.key) as List<String>, entry.value as List<String>))) {
        throw StateError('Could not verify restored preference ${entry.key}.');
      }
    }
  }

  bool _sameStringList(List<String> left, List<String> right) =>
      left.length == right.length && List.generate(left.length, (i) => left[i] == right[i]).every((same) => same);

  Future<void> _writeValue(
    SharedPreferences preferences,
    String key,
    Object value,
  ) async {
    if (value is bool) {
      if (!await preferences.setBool(key, value)) throw StateError('Could not restore $key.');
    } else if (value is int) {
      if (!await preferences.setInt(key, value)) throw StateError('Could not restore $key.');
    } else if (value is double) {
      if (!await preferences.setDouble(key, value)) throw StateError('Could not restore $key.');
    } else if (value is String) {
      if (!await preferences.setString(key, value)) throw StateError('Could not restore $key.');
    } else if (value is List<String>) {
      if (!await preferences.setStringList(key, value)) throw StateError('Could not restore $key.');
    } else {
      throw StateError('Unsupported preference value for key $key.');
    }
  }
}
