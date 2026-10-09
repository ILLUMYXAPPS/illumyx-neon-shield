import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import 'encrypted_file_vault.dart';

class EncryptedVaultScreen extends StatefulWidget {
  const EncryptedVaultScreen({super.key, this.vault});

  final EncryptedFileVault? vault;

  @override
  State<EncryptedVaultScreen> createState() => _EncryptedVaultScreenState();
}

class _EncryptedVaultScreenState extends State<EncryptedVaultScreen> {
  late final EncryptedFileVault _vault;
  List<VaultEntry> _entries = const [];
  bool _loading = true;
  bool _busy = false;
  String? _loadError;

  @override
  void initState() {
    super.initState();
    _vault = widget.vault ?? EncryptedFileVault();
    _refresh();
  }

  Future<void> _refresh() async {
    if (!mounted) return;
    setState(() {
      _loading = true;
      _loadError = null;
    });
    try {
      final entries = await _vault.listEntries();
      if (!mounted) return;
      setState(() {
        _entries = entries;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loadError = 'The vault index could not be read. Encrypted files were not changed.';
        _loading = false;
      });
    }
  }

  Future<void> _protectFile() async {
    if (_busy) return;
    final picked = await FilePicker.platform.pickFiles(
      type: FileType.any,
      allowMultiple: false,
      withData: true,
    );
    if (picked == null || picked.files.isEmpty || !mounted) return;
    final file = picked.files.single;
    final bytes = file.bytes;
    if (bytes == null) {
      _showMessage('This platform could not read the selected file. Try another file.');
      return;
    }
    if (bytes.isEmpty) {
      _showMessage('Empty files cannot be added to the vault.');
      return;
    }
    if (bytes.length > EncryptedFileVault.maxFileBytes) {
      _showMessage('Choose a file no larger than 50 MB for this beta.');
      return;
    }

    setState(() => _busy = true);
    try {
      final entry = await _vault.protectBytes(originalName: file.name, bytes: bytes);
      await _refresh();
      if (mounted) {
        _showMessage('${entry.name} encrypted into the local vault. Your original file was not changed.');
      }
    } catch (_) {
      if (mounted) _showMessage('The file could not be encrypted. The original file was not changed.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _restoreFile(VaultEntry entry) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final bytes = await _vault.decryptEntry(entry.id);
      if (!mounted) return;
      final savedPath = await FilePicker.platform.saveFile(
        dialogTitle: 'Save decrypted copy',
        fileName: entry.name,
        bytes: bytes,
      );
      if (mounted) {
        _showMessage(savedPath == null
            ? 'Save cancelled. The encrypted vault copy remains unchanged.'
            : 'Decrypted copy saved. The encrypted vault copy remains in place.');
      }
    } catch (_) {
      if (mounted) _showMessage('Could not decrypt this file. The encrypted vault copy was retained.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _removeEncryptedCopy(VaultEntry entry) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove encrypted copy?'),
        content: Text('This removes ${entry.name} from the vault only. It does not delete the original file or any decrypted copies.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Remove copy')),
        ],
      ),
    );
    if (confirmed != true || !mounted || _busy) return;
    setState(() => _busy = true);
    try {
      await _vault.removeEncryptedCopy(entry.id);
      await _refresh();
      if (mounted) _showMessage('Encrypted copy removed.');
    } catch (_) {
      if (mounted) _showMessage('Could not remove the encrypted copy.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _showMessage(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  String _formatSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Encrypted File Vault'),
        actions: [
          IconButton(
            tooltip: 'Refresh vault',
            onPressed: _busy ? null : _refresh,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: const Color(0xFF11172A),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: const Color(0xFF21E6FF).withValues(alpha: .35)),
            ),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.enhanced_encryption_rounded, size: 36, color: Color(0xFF21E6FF)),
                SizedBox(height: 12),
                Text('Encrypted copies stored on this device', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800)),
                SizedBox(height: 8),
                Text(
                  'Files are encrypted with AES-256-GCM before being written to the app vault. The key is kept in platform secure storage. Adding a file does not delete or modify the original.',
                  style: TextStyle(color: Color(0xFF9BA7C7), height: 1.45),
                ),
                SizedBox(height: 10),
                Text(
                  'Beta limits: 50 MB per file, files are read into memory, and there is no cloud backup or key recovery. Keep a separate backup of important originals.',
                  style: TextStyle(color: Color(0xFFFFD27A), height: 1.4, fontSize: 12),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _busy ? null : _protectFile,
            icon: const Icon(Icons.lock_rounded),
            label: Text(_busy ? 'Working…' : 'Encrypt a file'),
          ),
          const SizedBox(height: 18),
          const Text('VAULT CONTENTS', style: TextStyle(fontWeight: FontWeight.w800, letterSpacing: .6)),
          const SizedBox(height: 8),
          if (_loading)
            const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator()))
          else if (_loadError != null)
            _notice(_loadError!, isError: true)
          else if (_entries.isEmpty)
            _notice('Your encrypted vault is empty. Choose “Encrypt a file” to store a protected copy.')
          else
            for (final entry in _entries)
              Card(
                color: const Color(0xFF11172A),
                child: ListTile(
                  leading: const Icon(Icons.lock_rounded, color: Color(0xFF21E6FF)),
                  title: Text(entry.name, maxLines: 2, overflow: TextOverflow.ellipsis),
                  subtitle: Text('${_formatSize(entry.sizeBytes)} • ${entry.createdAt.toLocal().toString().substring(0, 16)}'),
                  isThreeLine: true,
                  trailing: PopupMenuButton<String>(
                    enabled: !_busy,
                    onSelected: (value) {
                      if (value == 'restore') _restoreFile(entry);
                      if (value == 'remove') _removeEncryptedCopy(entry);
                    },
                    itemBuilder: (context) => const [
                      PopupMenuItem(value: 'restore', child: Text('Decrypt / save copy')),
                      PopupMenuItem(value: 'remove', child: Text('Remove encrypted copy')),
                    ],
                  ),
                ),
              ),
        ],
      ),
    );
  }

  Widget _notice(String message, {bool isError = false}) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFF11172A),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Text(
          message,
          style: TextStyle(color: isError ? const Color(0xFFFF8B9A) : const Color(0xFF9BA7C7), height: 1.4),
        ),
      );
}
