import 'package:shared_preferences/shared_preferences.dart';

/// Mobile scheduling state for a user-confirmed posture-review reminder.
///
/// This deliberately does not claim to run a security scan in the background:
/// the current Flutter beta has no native posture-check engine, and iOS/Android
/// background execution is OS-controlled. This service only tracks reminders
/// while the app is open and stores minimal local evidence.
class SmartScanScheduleService {
  static const Duration interval = Duration(hours: 1);
  static const String _enabledKey = 'neon_shield.smart_scan.enabled';
  static const String _nextDueKey = 'neon_shield.smart_scan.next_due';
  static const String _lastReviewKey = 'neon_shield.smart_scan.last_review';
  static const String _lastStatusKey = 'neon_shield.smart_scan.last_status';

  Future<bool> isEnabled() async {
    final preferences = await SharedPreferences.getInstance();
    return preferences.getBool(_enabledKey) ?? true;
  }

  Future<void> setEnabled(bool enabled) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setBool(_enabledKey, enabled);
    if (enabled) {
      await preferences.setInt(
        _nextDueKey,
        DateTime.now().add(interval).millisecondsSinceEpoch,
      );
    }
  }

  Future<DateTime> nextDue() async {
    final preferences = await SharedPreferences.getInstance();
    final stored = preferences.getInt(_nextDueKey);
    if (stored == null) {
      final due = DateTime.now().add(interval);
      await preferences.setInt(_nextDueKey, due.millisecondsSinceEpoch);
      return due;
    }
    return DateTime.fromMillisecondsSinceEpoch(stored);
  }

  Future<bool> isDue() async {
    if (!await isEnabled()) return false;
    return !DateTime.now().isBefore(await nextDue());
  }

  Future<DateTime?> lastReview() async {
    final preferences = await SharedPreferences.getInstance();
    final value = preferences.getInt(_lastReviewKey);
    return value == null ? null : DateTime.fromMillisecondsSinceEpoch(value);
  }

  Future<String?> lastStatus() async {
    final preferences = await SharedPreferences.getInstance();
    return preferences.getString(_lastStatusKey);
  }

  /// Records only the timestamp and status. "verified_clear" is intentionally
  /// unavailable until actual supported security checks exist on mobile.
  Future<void> recordReviewAcknowledged() async {
    final preferences = await SharedPreferences.getInstance();
    final now = DateTime.now();
    await preferences.setInt(_lastReviewKey, now.millisecondsSinceEpoch);
    await preferences.setString(_lastStatusKey, 'review_acknowledged_not_verified');
    await preferences.setInt(
      _nextDueKey,
      now.add(interval).millisecondsSinceEpoch,
    );
  }
}
