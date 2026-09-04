import 'package:flutter_test/flutter_test.dart';
import 'package:illumyx_neon_shield/main.dart';

void main() {
  testWidgets('renders Neon Shield onboarding shell', (tester) async {
    await tester.pumpWidget(const NeonShieldApp());

    // Bootstrap performs asynchronous security-state loading and the onboarding
    // shell contains ongoing UI animation, so pump a bounded amount of time
    // instead of waiting for the entire widget tree to become idle.
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
