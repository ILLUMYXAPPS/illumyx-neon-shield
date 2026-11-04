import 'package:flutter/material.dart';

/// Customer-controlled, optional A.D. Bugsworth companion setting.
class AdBugsworthCard extends StatelessWidget {
  const AdBugsworthCard({
    super.key,
    required this.enabled,
    required this.onChanged,
  });

  final bool enabled;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: const Color(0xFF11172A),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: BorderSide(
          color: const Color(0xFF21E6FF).withValues(alpha: .25),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          children: [
            SwitchListTile(
              secondary: const CircleAvatar(
                backgroundColor: Color(0xFF24143A),
                child: Icon(Icons.bug_report_rounded, color: Color(0xFF21E6FF)),
              ),
              title: const Text(
                'A.D. Bugsworth',
                style: TextStyle(fontWeight: FontWeight.w800),
              ),
              subtitle: Text(
                enabled ? 'Your optional Shield companion is ON.' : 'Your optional Shield companion is OFF.',
                style: const TextStyle(color: Color(0xFF9BA7C7)),
              ),
              value: enabled,
              onChanged: onChanged,
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 0, 18, 10),
              child: Text(
                enabled
                    ? 'A.D. is here for a little encouragement. You are always in control.'
                    : 'A.D. will stay quietly tucked away until you choose to turn him on.',
                style: const TextStyle(color: Color(0xFF9BA7C7), height: 1.4),
              ),
            ),
            const Padding(
              padding: EdgeInsets.fromLTRB(18, 0, 18, 12),
              child: Text(
                'A.D. is a friendly companion only. This setting never changes scanning, protection, alerts, privacy, or security decisions.',
                style: TextStyle(fontSize: 12, color: Color(0xFF9BA7C7), height: 1.4),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
