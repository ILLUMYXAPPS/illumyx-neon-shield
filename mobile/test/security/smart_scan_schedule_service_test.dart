import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:illumyx_neon_shield/security/smart_scan_schedule_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late SmartScanScheduleService service;

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    service = SmartScanScheduleService();
  });

  test('defaults to enabled and initializes an hourly due time', () async {
    expect(await service.isEnabled(), isTrue);
    final due = await service.nextDue();
    final remaining = due.difference(DateTime.now());
    expect(remaining.inMinutes, inInclusiveRange(59, 60));
    expect(await service.isDue(), isFalse);
  });

  test('disabled schedule never reports due', () async {
    await service.setEnabled(false);
    expect(await service.isEnabled(), isFalse);
    expect(await service.isDue(), isFalse);
  });

  test('acknowledged review records a timestamp and non-verified status', () async {
    await service.recordReviewAcknowledged();
    expect(await service.lastReview(), isNotNull);
    expect(await service.lastStatus(), 'review_acknowledged_not_verified');
  });

  test('acknowledged review schedules the next reminder about one hour later', () async {
    await service.recordReviewAcknowledged();
    final due = await service.nextDue();
    expect(due.difference(DateTime.now()).inMinutes, inInclusiveRange(59, 60));
  });
}
