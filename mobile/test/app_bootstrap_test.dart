import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:illumyx_neon_shield/main.dart';
import 'package:illumyx_neon_shield/security/security_service.dart';

class _MemoryTrustedDeviceStore implements TrustedDeviceStore {
  List<String>? devices;

  @override
  Future<List<String>?> readTrustedDevices() async =>
      devices == null ? null : List<String>.from(devices!);

  @override
  Future<void> writeTrustedDevices(List<String> deviceIds) async {
    devices = List<String>.from(deviceIds);
  }
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'neon_shield.owner_initialized': false,
    });
  });

  testWidgets('fresh install completes local setup and opens the dashboard',
      (tester) async {
    final store = _MemoryTrustedDeviceStore();
    SecurityService createSecurityService() =>
        SecurityService(trustedDeviceStore: store);

    await tester.pumpWidget(
      MaterialApp(
        home: AppBootstrap(securityServiceFactory: createSecurityService, allowLocalBeta: true),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Your digital space, protected.'), findsOneWidget);

    for (var step = 0; step < 4; step++) {
      await tester.tap(find.text('Continue'));
      await tester.pumpAndSettle();
    }

    expect(find.text('Complete local setup'), findsOneWidget);
    await tester.tap(find.text('Complete local setup'));
    await tester.pumpAndSettle();

    expect(find.text('ILLUMYX NEON SHIELD'), findsOneWidget);
    expect(find.text('Posture Dashboard'), findsOneWidget);
    expect(find.text('Not active in this beta'), findsOneWidget);
    expect(
      find.textContaining('It does not scan files, block threats, or provide antivirus protection.'),
      findsOneWidget,
    );
    await tester.scrollUntilVisible(
      find.text('Local device records'),
      250,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Local device records'), findsOneWidget);
    await tester.drag(find.byType(ListView).first, const Offset(0, 1200));
    await tester.pumpAndSettle();
    expect(
      (await SharedPreferences.getInstance())
          .getBool('neon_shield.onboarding_complete'),
      isTrue,
    );

    final restored = createSecurityService();
    await restored.load();
    expect(restored.snapshot().ownerInitialized, isTrue);

    expect(find.text('Open encrypted file vault'), findsOneWidget);
    await tester.tap(find.text('Open encrypted file vault'));
    await tester.pumpAndSettle();
    expect(find.text('Encrypted File Vault'), findsOneWidget);
    expect(find.text('Encrypt a file'), findsOneWidget);
    expect(find.textContaining('The key is kept in platform secure storage.'), findsOneWidget);
  });

  testWidgets('stale completion flag cannot bypass missing owner setup',
      (tester) async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'neon_shield.onboarding_complete': true,
      'neon_shield.owner_initialized': false,
    });

    await tester.pumpWidget(
      MaterialApp(
        home: AppBootstrap(
          securityServiceFactory: () =>
              SecurityService(trustedDeviceStore: _MemoryTrustedDeviceStore()),
          allowLocalBeta: true,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Your digital space, protected.'), findsOneWidget);
    // The dashboard also uses the product name, so assert against its unique hero copy.
    expect(find.text('Mobile Shield Ready'), findsNothing);
  });
  testWidgets('dashboard stays locked when server auth is not configured',
      (tester) async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'neon_shield.onboarding_complete': true,
      'neon_shield.owner_initialized': true,
    });

    await tester.pumpWidget(
      MaterialApp(
        home: AppBootstrap(
          securityServiceFactory: () => SecurityService(
            trustedDeviceStore: _MemoryTrustedDeviceStore(),
          ),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    expect(find.text('Secure sign-in is not configured'), findsOneWidget);
    expect(find.text('Mobile Shield Ready'), findsNothing);
  });

}
