import 'package:flutter/material.dart';
import 'auth_session.dart';
import 'device_pairing_api.dart';

class ConnectedDevicesScreen extends StatefulWidget {
  const ConnectedDevicesScreen({super.key, required this.api, required this.session});
  final DevicePairingApi api;
  final AuthSession session;
  @override
  State<ConnectedDevicesScreen> createState() => _ConnectedDevicesScreenState();
}

class _ConnectedDevicesScreenState extends State<ConnectedDevicesScreen> {
  List<ConnectedDevice> _devices = const [];
  bool _loading = true;
  String? _error;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final devices = await widget.api.listDevices(widget.session);
      if (!mounted) return;
      setState(() { _devices = devices; _loading = false; });
    } catch (_) {
      if (!mounted) return;
      setState(() { _loading = false; _error = 'Connected devices could not be loaded. Check your connection and try again.'; });
    }
  }

  Future<void> _approve() async {
    final requestController = TextEditingController();
    final codeController = TextEditingController();
    final decision = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Approve or reject a device'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          const Text('Enter the request reference from the new device. Approve only if you started the request and the six-digit code matches. You can reject a request without entering its code.'),
          const SizedBox(height: 14),
          TextField(controller: requestController, decoration: const InputDecoration(labelText: 'Request reference')),
          const SizedBox(height: 10),
          TextField(controller: codeController, keyboardType: TextInputType.number, maxLength: 6, decoration: const InputDecoration(labelText: 'Six-digit code')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, 'cancel'), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(context, 'reject'), child: const Text('Reject request')),
          FilledButton(onPressed: () => Navigator.pop(context, 'approve'), child: const Text('Approve')),
        ],
      ),
    );
    final requestId = requestController.text.trim();
    final code = codeController.text.trim();
    requestController.dispose();
    codeController.dispose();
    if (decision == null || decision == 'cancel' || requestId.isEmpty) return;
    try {
      if (decision == 'reject') {
        await widget.api.rejectPairing(session: widget.session, requestId: requestId);
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Pairing request rejected.')));
      } else {
        await widget.api.approvePairing(session: widget.session, requestId: requestId, code: code);
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Device approved. It can now sign in.')));
      }
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(decision == 'reject' ? 'Rejection failed. Check the request reference and try again.' : 'Approval failed. Check the reference and code, then try again.')));
    }
    await _load();
  }

  Future<void> _rename(ConnectedDevice device) async {
    final controller = TextEditingController(text: device.name);
    final name = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Rename device'),
        content: TextField(controller: controller, maxLength: 48, decoration: const InputDecoration(labelText: 'Device name')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, controller.text.trim()), child: const Text('Save')),
        ],
      ),
    );
    controller.dispose();
    if (name == null || name.isEmpty) return;
    try {
      await widget.api.renameDevice(session: widget.session, deviceReference: device.reference, deviceName: name);
      await _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not rename this device.')));
    }
  }

  Future<void> _unlink(ConnectedDevice device) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Unlink device?'),
        content: Text('“${device.name}” will lose access to this account. Its active sessions will be revoked.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Keep device')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Unlink')),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await widget.api.unlinkDevice(session: widget.session, deviceReference: device.reference);
      await _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('This device could not be unlinked. You cannot unlink the device currently in use.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My Connected Devices')),
      floatingActionButton: FloatingActionButton.extended(onPressed: _approve, icon: const Icon(Icons.verified_user_rounded), label: const Text('Approve a device')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? ListView(children: [const SizedBox(height: 180), Center(child: CircularProgressIndicator())])
            : ListView(
                padding: const EdgeInsets.fromLTRB(18, 18, 18, 96),
                children: [
                  const Text('Your account, your devices.', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
                  const SizedBox(height: 6),
                  const Text('Only devices approved by this account appear here. Unlinking a device revokes its active sessions.', style: TextStyle(color: Color(0xFF9BA7C7), height: 1.4)),
                  if (_error != null) ...[
                    const SizedBox(height: 14),
                    Text(_error!, style: const TextStyle(color: Color(0xFFFF8B9A))),
                    TextButton(onPressed: _load, child: const Text('Retry')),
                  ],
                  const SizedBox(height: 18),
                  for (final device in _devices)
                    Card(
                      color: const Color(0xFF11172A),
                      child: ListTile(
                        leading: const Icon(Icons.devices_rounded, color: Color(0xFF21E6FF)),
                        title: Text(device.name),
                        subtitle: Text(device.addedAt == null ? 'Authorised device' : 'Added ${device.addedAt}'),
                        trailing: PopupMenuButton<String>(
                          onSelected: (value) => value == 'rename' ? _rename(device) : _unlink(device),
                          itemBuilder: (_) => const [
                            PopupMenuItem(value: 'rename', child: Text('Rename')),
                            PopupMenuItem(value: 'unlink', child: Text('Unlink')),
                          ],
                        ),
                      ),
                    ),
                  if (!_loading && _devices.isEmpty) const Text('No authorised devices were returned for this account.'),
                ],
              ),
      ),
    );
  }
}
