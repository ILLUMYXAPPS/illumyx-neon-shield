import 'dart:convert';

import 'package:crypto/crypto.dart';

/// Privacy-preserving phone access blocklist.
///
/// Phone numbers are normalized before hashing. Only SHA-256 hashes are stored
/// in the app source, so raw blocked numbers are not committed.
///
/// IMPORTANT: This service must be called by the authentication/backend layer
/// before granting access. The current beta has no phone authentication or
/// remote backend, so this is an enforcement component for that integration,
/// not a claim that the standalone beta can identify a caller's phone number.
class AccessBlocklist {
  AccessBlocklist._();

  static const Set<String> _blockedPhoneHashes = {
    '9605401255b50d556b4bcc07c442b65ac9cbd71691bd167ff18cc8249a3f251b',
    '4fe958cb52ca69de5de2cb3f532ecd7dff2c61c0e58bbc7070bd5853f7efb65',
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

  /// Add future, verified associations through the backend/admin blocklist.
  /// Do not infer ownership of a new number from a device identifier alone.
  static bool isBlockedHash(String hash) => _blockedPhoneHashes.contains(hash);
}
