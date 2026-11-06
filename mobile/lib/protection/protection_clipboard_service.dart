import 'package:shared_preferences/shared_preferences.dart';

class ProtectionClipboardControl {
  const ProtectionClipboardControl({
    required this.key,
    required this.title,
    required this.description,
  });

  final String key;
  final String title;
  final String description;
}

const protectionClipboardControls = <ProtectionClipboardControl>[
  ProtectionClipboardControl(
    key: 'device_security',
    title: 'Device security',
    description: 'Device posture and security checks.',
  ),
  ProtectionClipboardControl(
    key: 'privacy_protection',
    title: 'Privacy protection',
    description: 'Privacy-related protection preferences.',
  ),
  ProtectionClipboardControl(
    key: 'app_monitoring',
    title: 'App monitoring',
    description: 'Application monitoring preferences.',
  ),
  ProtectionClipboardControl(
    key: 'network_safety',
    title: 'Network safety',
    description: 'Network safety and connection checks.',
  ),
  ProtectionClipboardControl(
    key: 'family_safety',
    title: 'Family safety',
    description: 'Family safety preferences.',
  ),
  ProtectionClipboardControl(
    key: 'security_notifications',
    title: 'Security notifications',
    description: 'Security alert and notification preferences.',
  ),
];

class ProtectionClipboardService {
  static const _enabledKey = 'neon_shield.protection_clipboard.enabled';
  static const _controlPrefix = 'neon_shield.protection_clipboard.control.';

  Future<bool> loadEnabled() async {
    final preferences = await SharedPreferences.getInstance();
    return preferences.getBool(_enabledKey) ?? true;
  }

  Future<void> setEnabled(bool enabled) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setBool(_enabledKey, enabled);
  }

  Future<Map<String, bool>> loadControls() async {
    final preferences = await SharedPreferences.getInstance();
    return {
      for (final control in protectionClipboardControls)
        control.key: preferences.getBool('$_controlPrefix${control.key}') ?? true,
    };
  }

  Future<void> setControlEnabled(String key, bool enabled) async {
    final knownControl = protectionClipboardControls.any((control) => control.key == key);
    if (!knownControl) {
      throw ArgumentError.value(key, 'key', 'Unknown Protection Clipboard control');
    }
    final preferences = await SharedPreferences.getInstance();
    await preferences.setBool('$_controlPrefix$key', enabled);
  }
}
