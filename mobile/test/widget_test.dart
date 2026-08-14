import 'package:flutter_test/flutter_test.dart';
import 'package:illumyx_neon_shield/main.dart';

void main() {
  testWidgets('renders Neon Shield mobile shell', (tester) async {
    await tester.pumpWidget(const NeonShieldApp());
    expect(find.text('ILLUMYX NEON SHIELD'), findsOneWidget);
    expect(find.text('Mobile v1.0-beta'), findsOneWidget);
    expect(find.text('Secure. Smart. Neon.'), findsOneWidget);
  });
}
