import 'dart:convert';

import 'package:http/http.dart' as http;

import '../auth/auth_session.dart';

class FamilyInvitation {
  const FamilyInvitation({
    required this.id,
    required this.expiresAt,
    this.code,
  });

  final String id;
  final DateTime expiresAt;
  final String? code;

  factory FamilyInvitation.fromJson(Map<String, dynamic> json) {
    final id = json['invitation_id'];
    final expires = json['expires_at'];
    if (id is! String || id.isEmpty || expires is! String) {
      throw const FormatException('Invalid Family invitation');
    }
    return FamilyInvitation(
      id: id,
      expiresAt: DateTime.parse(expires).toLocal(),
      code: json['invitation_code'] is String ? json['invitation_code'] as String : null,
    );
  }
}

abstract interface class FamilyInvitationsApi {
  Future<FamilyInvitation> create(AuthSession session);
  Future<List<FamilyInvitation>> list(AuthSession session);
  Future<void> accept(AuthSession session, String code);
  Future<bool> revoke(AuthSession session, String invitationId);
}

class FamilyApiException implements Exception {
  const FamilyApiException(this.message);
  final String message;
  @override
  String toString() => message;
}

class HttpsFamilyInvitationsApi implements FamilyInvitationsApi {
  HttpsFamilyInvitationsApi({
    required Uri baseUri,
    http.Client? client,
  })  : _baseUri = baseUri,
        _client = client ?? http.Client() {
    final loopback = baseUri.host == '127.0.0.1' ||
        baseUri.host == 'localhost' ||
        baseUri.host == '::1';
    if ((baseUri.scheme != 'https' && !loopback) ||
        baseUri.host.isEmpty ||
        baseUri.userInfo.isNotEmpty) {
      throw ArgumentError('Family API requires a valid HTTPS endpoint');
    }
  }

  final Uri _baseUri;
  final http.Client _client;

  Uri _url(String path) => _baseUri.resolve(path);
  Map<String, String> _headers(AuthSession session) => {
        'Authorization': 'Bearer ${session.token}',
        'Content-Type': 'application/json',
      };

  Map<String, dynamic> _decode(http.Response response, Set<int> accepted) {
    Map<String, dynamic> data;
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is! Map<String, dynamic>) throw const FormatException();
      data = decoded;
    } catch (_) {
      throw const FamilyApiException('Neon Shield received an invalid response. Please try again.');
    }
    if (!accepted.contains(response.statusCode)) {
      final error = data['error'];
      final message = switch (error) {
        'active_premium_family_required' => 'An active Premium Family subscription is required to invite members.',
        'family_member_limit_reached' => 'Your Family plan has reached its five-member limit.',
        'account_already_in_a_family' => 'This account is already part of a Family household.',
        'account_already_in_another_family' => 'This account already belongs to another Family household.',
        'invalid_or_used_invitation' => 'That invitation code is invalid or has already been used.',
        'invitation_expired' => 'That invitation has expired. Ask the owner for a new code.',
        'owner_cannot_accept_own_invitation' => 'The Family owner cannot accept their own invitation.',
        'account_has_previous_family_membership' => 'This account has a previous Family membership that cannot be transferred.',
        'family_invitations_unavailable' => 'Family Management is temporarily unavailable.',
        _ => 'Family Management could not complete that request. Please try again.',
      };
      throw FamilyApiException(message);
    }
    return data;
  }

  @override
  Future<FamilyInvitation> create(AuthSession session) async {
    final response = await _client.post(
      _url('/v1/family/invitations'),
      headers: _headers(session),
      body: '{}',
    ).timeout(const Duration(seconds: 15));
    return FamilyInvitation.fromJson(_decode(response, {201}));
  }

  @override
  Future<List<FamilyInvitation>> list(AuthSession session) async {
    final response = await _client.get(
      _url('/v1/family/invitations'),
      headers: _headers(session),
    ).timeout(const Duration(seconds: 15));
    final data = _decode(response, {200});
    final rows = data['invitations'];
    if (rows is! List) {
      throw const FamilyApiException('The Family invitation list could not be read.');
    }
    return rows
        .whereType<Map<String, dynamic>>()
        .map(FamilyInvitation.fromJson)
        .toList(growable: false);
  }

  @override
  Future<void> accept(AuthSession session, String code) async {
    final response = await _client.post(
      _url('/v1/family/invitations/accept'),
      headers: _headers(session),
      body: jsonEncode({'invitation_code': code.trim()}),
    ).timeout(const Duration(seconds: 15));
    _decode(response, {200});
  }

  @override
  Future<bool> revoke(AuthSession session, String invitationId) async {
    final response = await _client.delete(
      _url('/v1/family/invitations/$invitationId'),
      headers: _headers(session),
    ).timeout(const Duration(seconds: 15));
    final data = _decode(response, {200});
    return data['revoked'] == true;
  }
}
