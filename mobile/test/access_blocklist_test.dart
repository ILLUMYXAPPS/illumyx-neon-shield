import 'package:flutter_test/flutter_test.dart';

import 'package:illumyx_neon_shield/security/access_blocklist.dart';

void main() {
  test('blocks the configured phone identities', () {
    expect(AccessBlocklist.isBlockedPhone('0422122753'), isTrue);
    expect(AccessBlocklist.isBlockedPhone('0427488809'), isTrue);
  });

  test('keeps the committed hash fixtures stable', () {
    expect(
      AccessBlocklist.hashPhone('0422122753'),
      '9605401255b50d556b4bcc07c442b65ac9cbd71691bd167ff18cc8249a3f251b',
    );
    expect(
      AccessBlocklist.hashPhone('0427488809'),
      '4fe958cb52ca69de5de2cb3f532ecd7dff2c61c0e58bbc7070bd585f3f7efb65',
    );
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
