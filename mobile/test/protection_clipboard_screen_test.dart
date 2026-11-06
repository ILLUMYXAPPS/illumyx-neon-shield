import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:illumyx_neon_shield/protection/protection_clipboard_screen.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  testWidgets('customer can switch the Protection Clipboard off and on',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: ProtectionClipboardScreen()),
    );
    await tester.pumpAndSettle();

    final masterSwitch = find.widgetWithText(
      SwitchListTile,
      'Protection Clipboard',
    );

    expect(tester.widget<SwitchListTile>(masterSwitch).value, isTrue);

    await tester.tap(masterSwitch);
    await tester.pumpAndSettle();

    expect(tester.widget<SwitchListTile>(masterSwitch).value, isFalse);
    expect(find.text('Disabled'), findsOneWidget);

    await tester.tap(masterSwitch);
    await tester.pumpAndSettle();

    expect(tester.widget<SwitchListTile>(masterSwitch).value, isTrue);
    expect(find.text('Enabled'), findsOneWidget);
  });

  testWidgets('master switch disables individual choices without erasing them',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: ProtectionClipboardScreen()),
    );
    await tester.pumpAndSettle();

    final deviceSwitch = find.widgetWithText(SwitchListTile, 'Device security');
    await tester.tap(deviceSwitch);
    await tester.pumpAndSettle();
    expect(tester.widget<SwitchListTile>(deviceSwitch).value, isFalse);

    final masterSwitch = find.widgetWithText(
      SwitchListTile,
      'Protection Clipboard',
    );
    await tester.tap(masterSwitch);
    await tester.pumpAndSettle();

    expect(tester.widget<SwitchListTile>(deviceSwitch).onChanged, isNull);

    // Turning the master control back on restores access to the saved choice.
    await tester.tap(masterSwitch);
    await tester.pumpAndSettle();
    expect(tester.widget<SwitchListTile>(deviceSwitch).onChanged, isNotNull);
    expect(tester.widget<SwitchListTile>(deviceSwitch).value, isFalse);
  });

  testWidgets('customer choices survive closing and reopening the screen',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: ProtectionClipboardScreen()),
    );
    await tester.pumpAndSettle();

    final privacySwitch = find.widgetWithText(
      SwitchListTile,
      'Privacy protection',
    );
    await tester.tap(privacySwitch);
    await tester.pumpAndSettle();

    await tester.pumpWidget(const MaterialApp(home: SizedBox.shrink()));
    await tester.pumpWidget(
      const MaterialApp(home: ProtectionClipboardScreen()),
    );
    await tester.pumpAndSettle();

    expect(tester.widget<SwitchListTile>(privacySwitch).value, isFalse);
  });
}
