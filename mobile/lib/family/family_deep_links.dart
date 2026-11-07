import 'dart:async';

import 'package:app_links/app_links.dart';

/// Custom-scheme invitation links work without a hosted website or domain
/// association file. The app's native platform projects register this scheme.
class FamilyInvitationLink {
  const FamilyInvitationLink._();

  static const scheme = 'neonshield';
  static const host = 'family';
  static const path = '/invite';

  static Uri create(String code) {
    final value = code.trim();
    if (value.isEmpty) {
      throw ArgumentError.value(code, 'code', 'Invitation code cannot be empty');
    }
    return Uri(
      scheme: scheme,
      host: host,
      path: path,
      queryParameters: {'code': value},
    );
  }

  static String? codeFrom(Uri? uri) {
    if (uri == null ||
        uri.scheme.toLowerCase() != scheme ||
        uri.host.toLowerCase() != host ||
        uri.path != path) {
      return null;
    }
    final code = uri.queryParameters['code']?.trim();
    if (code == null || code.isEmpty || code.length > 1024) return null;
    return code;
  }
}

class FamilyDeepLinkListener {
  FamilyDeepLinkListener({AppLinks? appLinks})
      : _appLinks = appLinks ?? AppLinks();

  final AppLinks _appLinks;
  StreamSubscription<Uri>? _subscription;

  Future<void> start(void Function(String code) onInvitationCode) async {
    await _subscription?.cancel();
    _subscription = _appLinks.uriLinkStream.listen((uri) {
      final code = FamilyInvitationLink.codeFrom(uri);
      if (code != null) onInvitationCode(code);
    }, onError: (Object _) {
      // Ignore malformed platform link events; normal app use continues.
    });

    try {
      final initial = await _appLinks.getInitialLink();
      final initialCode = FamilyInvitationLink.codeFrom(initial);
      if (initialCode != null) onInvitationCode(initialCode);
    } catch (_) {
      // A missing or malformed initial link must not prevent app startup.
    }
  }

  Future<void> dispose() async {
    await _subscription?.cancel();
    _subscription = null;
  }
}
