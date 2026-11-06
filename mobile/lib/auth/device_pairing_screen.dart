import 'dart:async';
import 'package:flutter/material.dart';
import 'device_pairing_api.dart';

class DevicePairingScreen extends StatefulWidget {
  const DevicePairingScreen({super.key, required this.api, required this.deviceIdProvider});
  final DevicePairingApi api;
  final Future<String> Function() deviceIdProvider;
  @override
  State<DevicePairingScreen> createState() => _DevicePairingScreenState();
}

class _DevicePairingScreenState extends State<DevicePairingScreen> {
  final _identity = TextEditingController();
  final _password = TextEditingController();
  final _name = TextEditingController(text: 'My Neon Shield device');
  DevicePairingRequest? _request;
  Timer? _poller;
  bool _busy = false;
  String? _error;
  String _status = 'Not started';

  @override
  void dispose() {
    _poller?.cancel();
    _identity.dispose();
    _password.dispose();
    _name.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    if (_busy) return;
    if (_identity.text.trim().isEmpty || _password.text.isEmpty || _name.text.trim().isEmpty) {
      setState(() => _error = 'Enter your account details and a name for this device.');
      return;
    }
    setState(() { _busy = true; _error = null; });
    try {
      final deviceId = await widget.deviceIdProvider();
      final request = await widget.api.startPairing(
        identity: _identity.text.trim(),
        credential: _password.text,
        deviceId: deviceId,
        deviceName: _name.text.trim(),
      );
      _password.clear();
      if (!mounted) return;
      setState(() { _request = request; _status = 'Waiting for approval'; _busy = false; });
      _poller?.cancel();
      _poller = Timer.periodic(const Duration(seconds: 3), (_) => _checkStatus());
      await _checkStatus();
    } catch (_) {
      if (!mounted) return;
      setState(() { _busy = false; _error = 'Could not start pairing. Check your details and connection, then try again.'; });
    }
  }

  Future<void> _checkStatus() async {
    final request = _request;
    if (request == null || !mounted) return;
    if (!request.expiresAt.isAfter(DateTime.now().toUtc())) {
      _poller?.cancel();
      setState(() => _status = 'Pairing request expired. Start again.');
      return;
    }
    try {
      final status = await widget.api.pairingStatus(requestId: request.requestId, secret: request.secret);
      if (!mounted) return;
      if (status == 'approved') {
        _poller?.cancel();
        setState(() => _status = 'Approved! This device can now sign in securely.');
      } else if (status == 'expired' || status == 'rejected') {
        _poller?.cancel();
        setState(() => _status = status == 'expired' ? 'Pairing request expired. Start again.' : 'Pairing request was rejected.');
      }
    } catch (_) {
      if (mounted) setState(() => _error = 'Pairing status could not be checked. Keep this screen open and retry.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final request = _request;
    return Scaffold(
      appBar: AppBar(title: const Text('Pair this device')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(22),
          children: [
            const Icon(Icons.devices_rounded, size: 54, color: Color(0xFF21E6FF)),
            const SizedBox(height: 14),
            const Text('One account. Your devices.', style: TextStyle(fontSize: 23, fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            const Text('Start pairing here, then approve the request from a device already signed in to your Neon Shield account.', style: TextStyle(color: Color(0xFF9BA7C7), height: 1.45)),
            const SizedBox(height: 22),
            TextField(controller: _identity, keyboardType: TextInputType.emailAddress, decoration: const InputDecoration(labelText: 'Account identity')),
            const SizedBox(height: 12),
            TextField(controller: _password, obscureText: true, decoration: const InputDecoration(labelText: 'Password')),
            const SizedBox(height: 12),
            TextField(controller: _name, maxLength: 48, decoration: const InputDecoration(labelText: 'Name this device')),
            const SizedBox(height: 12),
            FilledButton.icon(onPressed: _busy || request != null ? null : _start, icon: const Icon(Icons.link_rounded), label: Text(_busy ? 'Starting…' : 'Start secure pairing')),
            if (request != null) ...[
              const SizedBox(height: 24),
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(color: const Color(0xFF11172A), borderRadius: BorderRadius.circular(18), border: Border.all(color: const Color(0xFF21E6FF).withValues(alpha: .45))),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('YOUR PAIRING CODE', style: TextStyle(color: Color(0xFF9BA7C7), fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    SelectableText(request.code, style: const TextStyle(fontSize: 38, letterSpacing: 8, fontWeight: FontWeight.w900, color: Color(0xFF21E6FF))),
                    const SizedBox(height: 12),
                    const Text('On your already connected device, choose “Approve a device” and enter this code plus the request reference below. The code expires after five minutes.', style: TextStyle(color: Color(0xFF9BA7C7), height: 1.4)),
                    const SizedBox(height: 12),
                    const Text('REQUEST REFERENCE', style: TextStyle(color: Color(0xFF9BA7C7), fontSize: 11, fontWeight: FontWeight.bold)),
                    SelectableText(request.requestId, style: const TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 14),
                    Row(children: [const Icon(Icons.hourglass_bottom_rounded, color: Color(0xFF21E6FF), size: 18), const SizedBox(width: 8), Expanded(child: Text(_status, style: const TextStyle(fontWeight: FontWeight.w600)))]),
                    const SizedBox(height: 8),
                    Text('Expires ${request.expiresAt.toLocal()}', style: const TextStyle(fontSize: 12, color: Color(0xFF9BA7C7))),
                    if (_status.startsWith('Pairing request expired')) TextButton(onPressed: () => setState(() { _request = null; _status = 'Not started'; }), child: const Text('Start a new request')),
                  ],
                ),
              ),
            ],
            if (_error != null) ...[
              const SizedBox(height: 14),
              Text(_error!, style: const TextStyle(color: Color(0xFFFF8B9A))),
              TextButton(onPressed: _checkStatus, child: const Text('Retry status check')),
            ],
          ],
        ),
      ),
    );
  }
}
