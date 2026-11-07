import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:share_plus/share_plus.dart';

import '../auth/auth_session.dart';
import 'family_api.dart';

class FamilyManagementScreen extends StatefulWidget {
  const FamilyManagementScreen({
    super.key,
    required this.api,
    required this.session,
  });

  final FamilyInvitationsApi api;
  final AuthSession session;

  @override
  State<FamilyManagementScreen> createState() => _FamilyManagementScreenState();
}

class _FamilyManagementScreenState extends State<FamilyManagementScreen> {
  final _invitationCode = TextEditingController();
  List<FamilyInvitation> _pending = const [];
  FamilyInvitation? _newInvitation;
  bool _loading = true;
  bool _busy = false;
  String? _error;
  String? _notice;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  @override
  void dispose() {
    _invitationCode.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final invitations = await widget.api.list(widget.session);
      if (!mounted) return;
      setState(() {
        _pending = invitations;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error is FamilyApiException
            ? error.message
            : 'Could not connect to Family Management. Please try again.';
        _loading = false;
      });
    }
  }

  Future<void> _createInvitation() async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
      _notice = null;
    });
    try {
      final invitation = await widget.api.create(widget.session);
      if (!mounted) return;
      setState(() {
        _newInvitation = invitation;
        _busy = false;
      });
      await _refresh();
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error is FamilyApiException
            ? error.message
            : 'Could not create an invitation. Please try again.';
        _busy = false;
      });
    }
  }

  Future<void> _acceptInvitation() async {
    final code = _invitationCode.text.trim();
    if (code.isEmpty || _busy) return;
    setState(() {
      _busy = true;
      _error = null;
      _notice = null;
    });
    try {
      await widget.api.accept(widget.session, code);
      if (!mounted) return;
      _invitationCode.clear();
      setState(() {
        _notice = 'You have joined the Family household.';
        _busy = false;
      });
      await _refresh();
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error is FamilyApiException
            ? error.message
            : 'The invitation could not be accepted. Please try again.';
        _busy = false;
      });
    }
  }

  Future<void> _copyCode(String code) async {
    await Clipboard.setData(ClipboardData(text: code));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Invitation code copied.')),
    );
  }

  Future<void> _shareCode(FamilyInvitation invitation) async {
    final code = invitation.code;
    if (code == null) return;
    await Share.share(
      'Join my ILLUMYX Neon Shield Family. Open Neon Shield, choose Family Management, and enter this invitation code:\n\n$code\n\nThis code expires on ${invitation.expiresAt}.',
      subject: 'Neon Shield Family invitation',
    );
  }

  Future<void> _revoke(FamilyInvitation invitation) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final revoked = await widget.api.revoke(widget.session, invitation.id);
      if (!mounted) return;
      setState(() {
        _busy = false;
        _notice = revoked ? 'Invitation revoked.' : 'That invitation is no longer pending.';
        if (_newInvitation?.id == invitation.id) _newInvitation = null;
      });
      await _refresh();
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error = error is FamilyApiException
            ? error.message
            : 'Could not revoke that invitation. Please try again.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    const muted = Color(0xFF9BA7C7);
    const cyan = Color(0xFF21E6FF);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Family Management'),
        actions: [
          IconButton(
            tooltip: 'Refresh invitations',
            onPressed: _loading ? null : _refresh,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(22),
                gradient: const LinearGradient(
                  colors: [Color(0xFF11172A), Color(0xFF24143A)],
                ),
                border: Border.all(color: cyan.withValues(alpha: .4)),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.family_restroom_rounded, color: cyan, size: 38),
                  SizedBox(height: 12),
                  Text('Your Family, connected.', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
                  SizedBox(height: 7),
                  Text(
                    'Premium Family supports up to five people, with two trusted devices per person and ten devices across the household.',
                    style: TextStyle(color: muted, height: 1.45),
                  ),
                ],
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 14),
              _message(_error!, isError: true),
            ],
            if (_notice != null) ...[
              const SizedBox(height: 14),
              _message(_notice!),
            ],
            const SizedBox(height: 20),
            _sectionTitle('MANAGE YOUR FAMILY'),
            const SizedBox(height: 8),
            const Text(
              'Family owners can invite people using a secure, one-time code. Only the code holder can accept, and each person must sign in first.',
              style: TextStyle(color: muted, height: 1.4),
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: _busy ? null : _createInvitation,
              icon: const Icon(Icons.person_add_alt_1_rounded),
              label: Text(_busy ? 'Working…' : 'Create invitation'),
            ),
            if (_newInvitation?.code != null) ...[
              const SizedBox(height: 12),
              _newInvitationCard(_newInvitation!),
            ],
            const SizedBox(height: 18),
            _sectionTitle('PENDING INVITATIONS'),
            const SizedBox(height: 8),
            if (_loading)
              const Center(child: Padding(
                padding: EdgeInsets.all(18),
                child: CircularProgressIndicator(),
              ))
            else if (_pending.isEmpty)
              const Text(
                'No pending invitations. New invitations will appear here.',
                style: TextStyle(color: muted),
              )
            else
              for (final invitation in _pending)
                Card(
                  color: const Color(0xFF11172A),
                  child: ListTile(
                    leading: const Icon(Icons.mark_email_unread_outlined, color: cyan),
                    title: const Text('Invitation awaiting acceptance'),
                    subtitle: Text('Expires ${invitation.expiresAt.toLocal()}'),
                    trailing: IconButton(
                      tooltip: 'Revoke invitation',
                      onPressed: _busy ? null : () => _revoke(invitation),
                      icon: const Icon(Icons.cancel_outlined, color: Color(0xFFFF8B9A)),
                    ),
                  ),
                ),
            const SizedBox(height: 24),
            _sectionTitle('JOIN A FAMILY'),
            const SizedBox(height: 8),
            const Text(
              'Have an invitation code? Sign in with your own Neon Shield account, then enter the code below to choose to join.',
              style: TextStyle(color: muted, height: 1.4),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _invitationCode,
              autocorrect: false,
              enableSuggestions: false,
              textCapitalization: TextCapitalization.none,
              onChanged: (_) => setState(() {}),
              decoration: const InputDecoration(
                labelText: 'Family invitation code',
                hintText: 'Paste your one-time code',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: _busy || _invitationCode.text.trim().isEmpty
                  ? null
                  : _acceptInvitation,
              icon: const Icon(Icons.group_add_rounded),
              label: const Text('Accept invitation'),
            ),
            const SizedBox(height: 16),
            const Text(
              'Privacy note: each member signs in with their own account. Family membership does not share passwords or expose another member’s private account details.',
              style: TextStyle(color: muted, fontSize: 12, height: 1.4),
            ),
          ],
        ),
      ),
    );
  }

  Widget _newInvitationCard(FamilyInvitation invitation) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFF11172A),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFF21E6FF).withValues(alpha: .35)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('YOUR NEW INVITATION CODE', style: TextStyle(color: Color(0xFF9BA7C7), fontSize: 11, fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            SelectableText(
              invitation.code!,
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, letterSpacing: 1.2),
            ),
            const SizedBox(height: 8),
            Text('Expires ${invitation.expiresAt}', style: const TextStyle(color: Color(0xFF9BA7C7), fontSize: 12)),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton.icon(
                  onPressed: () => _copyCode(invitation.code!),
                  icon: const Icon(Icons.copy_rounded),
                  label: const Text('Copy code'),
                ),
                FilledButton.icon(
                  onPressed: () => _shareCode(invitation),
                  icon: const Icon(Icons.share_rounded),
                  label: const Text('Share invitation'),
                ),
                TextButton.icon(
                  onPressed: _busy ? null : () => _revoke(invitation),
                  icon: const Icon(Icons.block_rounded),
                  label: const Text('Revoke'),
                ),
              ],
            ),
          ],
        ),
      );

  Widget _sectionTitle(String value) => Text(
        value,
        style: const TextStyle(
          fontSize: 12,
          color: Color(0xFF21E6FF),
          fontWeight: FontWeight.w800,
          letterSpacing: 1.1,
        ),
      );

  Widget _message(String value, {bool isError = false}) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: const Color(0xFF11172A),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isError ? const Color(0xFFFF8B9A) : const Color(0xFF21E6FF),
          ),
        ),
        child: Text(
          value,
          style: TextStyle(color: isError ? const Color(0xFFFF8B9A) : const Color(0xFF21E6FF)),
        ),
      );
}
