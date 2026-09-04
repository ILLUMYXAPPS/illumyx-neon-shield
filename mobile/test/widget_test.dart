import 'package:flutter_test/flutter_test.dart';
import 'package:illumyx_neon_shield/main.dart';

void main() {
  testWidgets('renders Neon Shield onboarding shell', (tester) async {
    await tester.pumpWidget(const NeonShieldApp());
    await tester.pumpAndSettle();

    expect(find.text('ILLUMYX NEON SHIELD'), findsOneWidget);
    expect(find.text('Your digital space, protected.'), findsOneWidget);
    expect(find.text('1/5'), findsOneWidget);
    expect(find.text('Continue'), findsOneWidget);
    expect(find.text('Privacy-first setup • Security boundaries remain enforced'), findsOneWidget);
  });
}
