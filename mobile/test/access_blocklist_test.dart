import 'package:flutter_test/flutter_test.dart';

import 'package:illumyx_neon_shield/security/access_blocklist.dart';

void main() {
  test('blocks the configured phone identities', () {
    expect(AccessBlocklist.isBlockedPhone('0422122753'), isTrue);
    expect(AccessBlocklist.isBlockedPhone('0427488809'), isTrue);
  });

  test('normalizes punctuation, spaces, and Australian +61 format', () {
    expect(AccessBlocklist.isBlockedPhone('04 2212 2753'), isTrue);
    expect(AccessBlocklist.isBlockedPhone('+61 422 122 753'), isTrue);
    expect(AccessBlocklist.isBlockedPhone('+61 427 488 809'), isTrue);
  });

  test('does not block an unrelated phone identity', () {
    expect(AccessBlocklist.isBlockedPhone('0400000000'), isFalse);
  });

  test('empty input is not treated as blocked', () {
    expect(AccessBlocklist.isBlockedPhone(''), isFalse);
  });
}
