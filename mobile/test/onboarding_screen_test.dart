import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:illumyx_neon_shield/onboarding/onboarding_screen.dart';

void main() {
  testWidgets('onboarding advances through all steps and completes', (tester) async {
    var completed = false;

    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData.dark(useMaterial3: true),
        home: OnboardingScreen(onComplete: () => completed = true),
      ),
    );

    expect(find.text('Your digital space, protected.'), findsOneWidget);
    expect(find.text('1/5'), findsOneWidget);

    for (var step = 2; step <= 5; step++) {
      await tester.tap(find.text('Continue'));
      await tester.pumpAndSettle();
      expect(find.text('$step/5'), findsOneWidget);
    }

    expect(find.text('Protection setup'), findsOneWidget);
    expect(find.text('Enter Neon Shield'), findsOneWidget);

    await tester.tap(find.text('Enter Neon Shield'));
    await tester.pumpAndSettle();

    expect(completed, isTrue);
  });

  testWidgets('back navigation returns to the previous step', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData.dark(useMaterial3: true),
        home: OnboardingScreen(onComplete: () {}),
      ),
    );

    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();
    expect(find.text('2/5'), findsOneWidget);

    await tester.tap(find.text('Back'));
    await tester.pumpAndSettle();
    expect(find.text('1/5'), findsOneWidget);
    expect(find.text('Your digital space, protected.'), findsOneWidget);
  });

  testWidgets('final step keeps both navigation and completion actions reachable', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData.dark(useMaterial3: true),
        home: OnboardingScreen(onComplete: () {}),
      ),
    );

    for (var step = 1; step < 5; step++) {
      await tester.tap(find.text('Continue'));
      await tester.pumpAndSettle();
    }

    expect(find.text('5/5'), findsOneWidget);
    expect(find.text('Back'), findsOneWidget);
    expect(find.text('Enter Neon Shield'), findsOneWidget);
  });
}
