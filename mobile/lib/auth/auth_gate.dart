import 'dart:async';

import 'package:flutter/material.dart';

import 'auth_api_contract.dart';
import 'auth_service.dart';
import 'auth_session.dart';

/// Fails closed until the server confirms a live, trusted session.
class AuthGate extends StatefulWidget {
  const AuthGate({
    super.key,
    required this.authService,
    required this.deviceIdProvider,
    required this.dashboardBuilder,
  });

  final AuthService authService;
  final Future<String> Function() deviceIdProvider;
  final Widget Function(VoidCallback onSignOut) dashboardBuilder;

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  final _identity = TextEditingController();
  final _credential = TextEditingController();
  AuthSession? _session;
  Timer? _expiryTimer;
  bool _checking = true;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _restore();
  }

  @override
  void dispose() {
    _expiryTimer?.cancel();
    _identity.dispose();
    _credential.dispose();
    super.dispose();
  }

  void _scheduleExpiry(AuthSession session) {
    _expiryTimer?.cancel();
    final remaining = session.expiresAt.toUtc().difference(DateTime.now().toUtc());
    if (remaining <= Duration.zero) {
      _expireSession(session);
      return;
    }
    _expiryTimer = Timer(remaining, () => _expireSession(session));
  }

  void _expireSession(AuthSession session) {
    if (!mounted || !identical(_session, session)) return;

    // Lock the dashboard immediately, then best-effort revoke and clear local
    // credentials through the service. A failed network call must not keep the
    // expired session visible in the UI.
    setState(() {
      _session = null;
      _error = 'Your session has expired. Please sign in again.';
    });
    widget.authService.signOut(session).catchError((Object _) {
      // Server revocation may fail offline; the service still clears local
      // credentials in its finally block.
    });
  }

  Future<void> _restore() async {
    if (mounted) setState(() { _checking = true; _error = null; });
    try {
      final restored = await widget.authService.restoreSession();
      if (!mounted) return;
      if (restored != null && restored.isExpired) {
        setState(() {
          _session = null;
          _checking = false;
          _error = 'Your session has expired. Please sign in again.';
        });
        await widget.authService.signOut(restored).catchError((Object _) {});
        return;
      }
      setState(() {
        _session = restored;
        _checking = false;
      });
      if (restored != null) _scheduleExpiry(restored);
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _session = null;
        _checking = false;
        _error = 'Neon Shield could not verify your session. Check your connection and try again.';
      });
    }
  }

  Future<void> _signIn() async {
    if (_busy) return;
    final identity = _identity.text.trim();
    final credential = _credential.text;
    if (identity.isEmpty || credential.isEmpty) {
      setState(() => _error = 'Enter your account identity and password.');
      return;
    }

    setState(() { _busy = true; _error = null; });
    try {
      final deviceId = await widget.deviceIdProvider();
      final session = await widget.authService.signIn(
        identity: identity,
        credential: credential,
        deviceId: deviceId,
      );
      if (!mounted) return;
      if (session.isExpired) {
        await widget.authService.signOut(session).catchError((Object _) {});
        setState(() {
          _session = null;
          _credential.clear();
          _busy = false;
          _error = 'The server returned an expired session. Please try again.';
        });
        return;
      }
      _expiryTimer?.cancel();
      setState(() {
        _session = session;
        _credential.clear();
        _busy = false;
      });
      _scheduleExpiry(session);
    } catch (error) {
      if (!mounted) return;
      final failure = error is AuthServiceException ? error.failure : AuthFailure.unavailable;
      setState(() {
        _busy = false;
        _error = switch (failure) {
          AuthFailure.invalidCredentials => 'Those sign-in details were not accepted.',
          AuthFailure.blockedIdentity => 'This account cannot sign in. Contact support if you believe this is an error.',
          AuthFailure.untrustedDevice => 'This device has not been approved for this account.',
          AuthFailure.rateLimited => 'Too many attempts. Please wait before trying again.',
          AuthFailure.expiredSession || AuthFailure.revokedSession => 'Your session is no longer valid. Please sign in again.',
          AuthFailure.unavailable => 'Authentication is unavailable. Check your connection and try again.',
        };
      });
    }
  }

  Future<void> _signOut() async {
    final session = _session;
    _expiryTimer?.cancel();
    setState(() { _busy = true; _error = null; });
    try {
      if (session != null) await widget.authService.signOut(session);
    } catch (_) {
      // The service clears local credentials in its finally block.
      if (mounted) {
        setState(() => _error = 'Signed out locally. The server could not confirm revocation.');
      }
    } finally {
      if (mounted) setState(() { _session = null; _busy = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_session != null && !_session!.isExpired) {
      return widget.dashboardBuilder(_signOut);
    }
    if (_session != null && _session!.isExpired) {
      // Do not render the dashboard even if the event loop has not delivered
      // the expiry timer yet.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && _session != null) _expireSession(_session!);
      });
    }
    if (_checking) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.shield_rounded, size: 68, color: Color(0xFF21E6FF)),
                  const SizedBox(height: 18),
                  const Text(
                    'ILLUMYX NEON SHIELD',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 23, fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    'Sign in through the configured secure service. Local setup alone does not grant dashboard access.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Color(0xFF9BA7C7), height: 1.45),
                  ),
                  const SizedBox(height: 28),
                  TextField(
                    controller: _identity,
                    keyboardType: TextInputType.emailAddress,
                    autofillHints: const [AutofillHints.username],
                    textInputAction: TextInputAction.next,
                    decoration: const InputDecoration(labelText: 'Account identity'),
                  ),
                  const SizedBox(height: 14),
                  TextField(
                    controller: _credential,
                    obscureText: true,
                    autofillHints: const [AutofillHints.password],
                    onSubmitted: (_) => _signIn(),
                    decoration: const InputDecoration(labelText: 'Password'),
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 14),
                    Text(_error!, style: const TextStyle(color: Color(0xFFFF8B9A))),
                  ],
                  const SizedBox(height: 22),
                  FilledButton(
                    onPressed: _busy ? null : _signIn,
                    child: Text(_busy ? 'Verifying…' : 'Sign in securely'),
                  ),
                  TextButton(
                    onPressed: _busy ? null : _restore,
                    child: const Text('Retry session verification'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
