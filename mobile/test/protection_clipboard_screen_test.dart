import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:illumyx_neon_shield/protection/protection_clipboard_screen.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  testWidgets('customer can switch the Protection Clipboard on and off',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: ProtectionClipboardScreen()),
    );
    await tester.pumpAndSettle();

    final masterSwitch = find.widgetWithText(
      SwitchListTile,
      'Protection Clipboard',
    );

    // New installations begin with the master control OFF.
    expect(tester.widget<SwitchListTile>(masterSwitch).value, isFalse);
    expect(find.text('Disabled'), findsOneWidget);

    await tester.tap(masterSwitch);
    await tester.pumpAndSettle();

    expect(tester.widget<SwitchListTile>(masterSwitch).value, isTrue);
    expect(find.text('Enabled'), findsOneWidget);

    await tester.tap(masterSwitch);
    await tester.pumpAndSettle();

    expect(tester.widget<SwitchListTile>(masterSwitch).value, isFalse);
    expect(find.text('Disabled'), findsOneWidget);
  });

  testWidgets('master switch disables individual choices without erasing them',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: ProtectionClipboardScreen()),
    );
    await tester.pumpAndSettle();

    final deviceSwitch = find.widgetWithText(SwitchListTile, 'Device security');
    final masterSwitch = find.widgetWithText(
      SwitchListTile,
      'Protection Clipboard',
    );

    // Individual choices are locked until the customer enables the master.
    expect(tester.widget<SwitchListTile>(deviceSwitch).value, isFalse);
    expect(tester.widget<SwitchListTile>(deviceSwitch).onChanged, isNull);

    await tester.tap(masterSwitch);
    await tester.pumpAndSettle();
    expect(tester.widget<SwitchListTile>(masterSwitch).value, isTrue);

    await tester.tap(deviceSwitch);
    await tester.pumpAndSettle();
    expect(tester.widget<SwitchListTile>(deviceSwitch).value, isTrue);

    await tester.tap(masterSwitch);
    await tester.pumpAndSettle();

    expect(tester.widget<SwitchListTile>(deviceSwitch).onChanged, isNull);
    expect(tester.widget<SwitchListTile>(deviceSwitch).value, isTrue);

    // Turning the master control back on restores access to the saved choice.
    await tester.tap(masterSwitch);
    await tester.pumpAndSettle();
    expect(tester.widget<SwitchListTile>(deviceSwitch).onChanged, isNotNull);
    expect(tester.widget<SwitchListTile>(deviceSwitch).value, isTrue);
  });

  testWidgets('customer choices survive closing and reopening the screen',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: ProtectionClipboardScreen()),
    );
    await tester.pumpAndSettle();

    final masterSwitch = find.widgetWithText(
      SwitchListTile,
      'Protection Clipboard',
    );
    await tester.tap(masterSwitch);
    await tester.pumpAndSettle();

    final privacySwitch = find.widgetWithText(
      SwitchListTile,
      'Privacy protection',
    );
    await tester.tap(privacySwitch);
    await tester.pumpAndSettle();
    expect(tester.widget<SwitchListTile>(privacySwitch).value, isTrue);

    await tester.pumpWidget(const MaterialApp(home: SizedBox.shrink()));
    await tester.pumpWidget(
      const MaterialApp(home: ProtectionClipboardScreen()),
    );
    await tester.pumpAndSettle();

    final reopenedPrivacySwitch = find.widgetWithText(
      SwitchListTile,
      'Privacy protection',
    );
    expect(tester.widget<SwitchListTile>(reopenedPrivacySwitch).value, isTrue);
  });

  testWidgets('settings load failure can be retried after storage is available',
      (tester) async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'neon_shield.protection_clipboard.enabled': 'invalid-type',
    });

    await tester.pumpWidget(
      const MaterialApp(home: ProtectionClipboardScreen()),
    );
    await tester.pumpAndSettle();

    expect(
      find.textContaining('Your saved settings could not be loaded'),
      findsOneWidget,
    );
    expect(find.text('Retry loading settings'), findsOneWidget);

    SharedPreferences.setMockInitialValues(<String, Object>{});
    await tester.tap(find.text('Retry loading settings'));
    await tester.pumpAndSettle();

    expect(find.text('Protection Clipboard'), findsOneWidget);
    expect(find.text('Disabled'), findsOneWidget);
    expect(find.text('Retry loading settings'), findsNothing);
  });

}
