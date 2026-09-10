import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:illumyx_neon_shield/onboarding/onboarding_screen.dart';

void main() {
  testWidgets('renders Neon Shield onboarding shell', (tester) async {
    // Test the onboarding UI directly. Bootstrap/security-state behavior is
    // covered by the security and onboarding tests; this keeps the widget
    // smoke test independent of platform secure-storage plugins.
    await tester.pumpWidget(
      const MaterialApp(
        home: OnboardingScreen(onComplete: _noop),
      ),
    );

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

void _noop() {}
