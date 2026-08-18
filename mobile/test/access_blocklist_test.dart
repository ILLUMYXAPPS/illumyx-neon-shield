import 'package:flutter_test/flutter_test.dart';
import 'package:illumyx_neon_shield/access_blocklist.dart';

void main() {
  test('blocks the configured phone numbers', () {
    expect(AccessBlocklist.isBlockedPhone('0422122753'), isTrue);
    expect(AccessBlocklist.isBlockedPhone('0427488809'), isTrue);
  });

  test('normalizes punctuation and spaces before checking', () {
    expect(AccessBlocklist.isBlockedPhone('04 2212 2753'), isTrue);
    expect(AccessBlocklist.isBlockedPhone('+61 422 122 753'), isTrue);
  });

  test('does not block an unrelated number', () {
    expect(AccessBlocklist.isBlockedPhone('0400000000'), isFalse);
  });

  test('empty input is not treated as blocked', () {
    expect(AccessBlocklist.isBlockedPhone(''), isFalse);
  });
}
