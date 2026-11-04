import 'package:shared_preferences/shared_preferences.dart';

/// Stores the customer's optional A.D. Bugsworth companion preference.
///
/// The companion is disabled by default. This preference never changes,
/// enables, or disables any security control.
class AdBugsworthSettings {
  static const preferenceKey = 'neon_shield.ad_bugsworth_enabled';

  Future<bool> loadEnabled() async {
    final preferences = await SharedPreferences.getInstance();
    return preferences.getBool(preferenceKey) ?? false;
  }

  Future<void> saveEnabled(bool enabled) async {
    final preferences = await SharedPreferences.getInstance();
    final saved = await preferences.setBool(preferenceKey, enabled);
    if (!saved) {
      throw StateError('A.D. Bugsworth preference could not be saved.');
    }
  }
}
