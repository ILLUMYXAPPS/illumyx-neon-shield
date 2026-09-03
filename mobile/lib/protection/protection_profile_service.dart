import 'package:shared_preferences/shared_preferences.dart';

import 'protection_profile.dart';

class ProtectionProfileService {
  static const _selectedProfileKey = 'neon_shield.protection_profile';

  Future<String> loadSelectedKey() async {
    final preferences = await SharedPreferences.getInstance();
    return preferences.getString(_selectedProfileKey) ?? 'music_audio';
  }

  Future<ProtectionProfile> loadSelected() async {
    final key = await loadSelectedKey();
    try {
      return profileForKey(key);
    } on ArgumentError {
      return profileForKey('music_audio');
    }
  }

  Future<void> select(String key) async {
    profileForKey(key);
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(_selectedProfileKey, key);
  }
}
