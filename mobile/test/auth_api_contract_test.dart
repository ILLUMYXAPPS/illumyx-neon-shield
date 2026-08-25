import 'package:flutter_test/flutter_test.dart';
import 'package:illumyx_neon_shield/auth/auth_api_contract.dart';

void main() {
  test('auth failure states remain explicit', () {
    expect(AuthFailure.values, containsAll(<AuthFailure>[
      AuthFailure.invalidCredentials,
      AuthFailure.expiredSession,
      AuthFailure.revokedSession,
      AuthFailure.untrustedDevice,
      AuthFailure.rateLimited,
      AuthFailure.unavailable,
    ]));
  });

  test('audit operation names cover the contract', () {
    expect(AuthOperation.values, containsAll(<AuthOperation>[
      AuthOperation.signIn,
      AuthOperation.refresh,
      AuthOperation.revoke,
      AuthOperation.trustedDeviceCheck,
    ]));
  });
}
