import 'package:flutter/material.dart';

import 'protection_clipboard_service.dart';

class ProtectionClipboardScreen extends StatefulWidget {
  const ProtectionClipboardScreen({super.key});

  @override
  State<ProtectionClipboardScreen> createState() => _ProtectionClipboardScreenState();
}

class _ProtectionClipboardScreenState extends State<ProtectionClipboardScreen> {
  final ProtectionClipboardService _service = ProtectionClipboardService();
  bool _loading = true;
  bool _enabled = true;
  Map<String, bool> _controls = const {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final enabled = await _service.loadEnabled();
      final controls = await _service.loadControls();
      if (!mounted) return;
      setState(() {
        _enabled = enabled;
        _controls = controls;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _loading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not load Protection Clipboard settings.')),
      );
    }
  }

  Future<void> _setMaster(bool value) async {
    final previous = _enabled;
    setState(() => _enabled = value);
    try {
      await _service.setEnabled(value);
    } catch (_) {
      if (!mounted) return;
      setState(() => _enabled = previous);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not save this setting. Please try again.')),
      );
    }
  }

  Future<void> _setControl(String key, bool value) async {
    final previous = _controls[key] ?? true;
    setState(() => _controls = {..._controls, key: value});
    try {
      await _service.setControlEnabled(key, value);
    } catch (_) {
      if (!mounted) return;
      setState(() => _controls = {..._controls, key: previous});
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not save this setting. Please try again.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Protection Clipboard')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(18),
              children: [
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    color: const Color(0xFF11172A),
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: const Color(0xFF21E6FF).withValues(alpha: .35)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.assignment_turned_in_rounded, color: Color(0xFF21E6FF)),
                          SizedBox(width: 10),
                          Expanded(
                            child: Text('YOUR PROTECTION CHOICES',
                                style: TextStyle(fontWeight: FontWeight.w800)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Choose which protection preferences are switched on. You can change these choices at any time.',
                        style: TextStyle(color: Color(0xFF9BA7C7), height: 1.4),
                      ),
                      const SizedBox(height: 12),
                      Material(
                        color: Colors.transparent,
                        child: SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          title: const Text('Protection Clipboard'),
                          subtitle: Text(_enabled ? 'Enabled' : 'Disabled'),
                          value: _enabled,
                          onChanged: _setMaster,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 14),
                for (final control in protectionClipboardControls)
                  Card(
                    color: const Color(0xFF11172A),
                    child: SwitchListTile(
                      title: Text(control.title),
                      subtitle: Text(control.description),
                      value: _controls[control.key] ?? true,
                      onChanged: _enabled ? (value) => _setControl(control.key, value) : null,
                    ),
                  ),
                const SizedBox(height: 12),
                const Text(
                  'Important beta note: these are saved customer preferences. Switching an option on does not, by itself, activate scanning, monitoring, threat blocking, or other enforcement. Those capabilities must be implemented and verified separately.',
                  style: TextStyle(color: Color(0xFF9BA7C7), height: 1.45, fontSize: 12),
                ),
              ],
            ),
    );
  }
}
