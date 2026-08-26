import 'dart:convert';

import 'package:crypto/crypto.dart';

/// Privacy-preserving phone access blocklist.
///
/// Phone numbers are normalized before hashing. Only SHA-256 hashes are stored
/// in the app source; raw blocked numbers are not committed.
///
/// This is an access-control input, not an identity provider. A phone number
/// must come from an authoritative authentication layer before this policy is
/// evaluated.
class AccessBlocklist {
  AccessBlocklist._();

  static const Set<String> _blockedPhoneHashes = {
    '9605401255b50d556b4bcc07c442b65ac9cbd71691bd167ff18cc8249a3f251b',
    '4fe958cb52ca69de5de2cb3f532ecd7dff2c61c0e58bbc7070bd585f3f7efb65',
    '9155a4747c0f402956eb6741ce1a832a945686b364a1e3bbc56beaafaac43309',
    'de73f46d41e9a225f767c310b342a596ec8640dfdaa98c42b3ad23c9c259247e',
    '6a3e13fe4ca63e99c4b586274a32e66251856a69c08e46aa566f1c90df96024a',
  };

  static String normalizePhone(String phone) {
    final digits = phone.replaceAll(RegExp(r'\D'), '');
    if (digits.startsWith('61') && digits.length == 11) {
      return '0${digits.substring(2)}';
    }
    return digits;
  }

  static String hashPhone(String phone) {
    final normalized = normalizePhone(phone);
    return sha256.convert(utf8.encode(normalized)).toString();
  }

  static bool isBlockedPhone(String phone) {
    final normalized = normalizePhone(phone);
    if (normalized.isEmpty) return false;
    return _blockedPhoneHashes.contains(hashPhone(normalized));
  }
}
