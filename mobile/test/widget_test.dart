import 'package:flutter_test/flutter_test.dart';
import 'package:illumyx_neon_shield/main.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  testWidgets('renders Neon Shield onboarding shell', (tester) async {
    // Isolate bootstrap state so a persisted onboarding/owner value from
    // another test cannot change the first-run screen under test.
    SharedPreferences.setMockInitialValues(<String, Object>{});

    await tester.pumpWidget(const NeonShieldApp());
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('ILLUMYX NEON SHIELD'), findsOneWidget);
    expect(find.text('Your digital space, protected.'), findsOneWidget);
    expect(find.text('1/5'), findsOneWidget);
    expect(find.text('Continue'), findsOneWidget);
    expect(
      find.text('Privacy-first setup • Security boundaries remain enforced'),
      findsOneWidget,
    );
  });
}
