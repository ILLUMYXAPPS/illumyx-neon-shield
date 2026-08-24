import 'package:flutter/material.dart';

class EvidenceDetail {
  const EvidenceDetail({
    required this.evidenceId,
    required this.recordedAt,
    required this.source,
    required this.candidate,
    required this.matchType,
    required this.confidence,
    required this.sourceSha256,
    required this.candidateSha256,
    required this.reviewStatus,
    required this.detail,
  });

  final String evidenceId;
  final String recordedAt;
  final String source;
  final String candidate;
  final String matchType;
  final double confidence;
  final String sourceSha256;
  final String candidateSha256;
  final String reviewStatus;
  final String detail;
}

class EvidenceDetailView extends StatelessWidget {
  const EvidenceDetailView({super.key, required this.evidence});

  final EvidenceDetail evidence;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Evidence Detail')),
      body: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          _notice(),
          const SizedBox(height: 16),
          _section('IDENTITY', [
            _row('Evidence ID', evidence.evidenceId),
            _row('Recorded', evidence.recordedAt),
            _row('Review status', evidence.reviewStatus),
          ]),
          _section('MATCH', [
            _row('Source', evidence.source),
            _row('Candidate', evidence.candidate),
            _row('Match type', evidence.matchType),
            _row('Confidence', '${evidence.confidence.toStringAsFixed(1)}%'),
          ]),
          _section('FINGERPRINTS', [
            _row('Source SHA-256', evidence.sourceSha256),
            _row('Candidate SHA-256', evidence.candidateSha256),
          ]),
          _section('DETAIL', [
            Padding(
              padding: const EdgeInsets.all(16),
              child: Text(evidence.detail, style: const TextStyle(height: 1.45)),
            ),
          ]),
          const SizedBox(height: 8),
          const Text(
            'This record is evidence for human review. It is not an automatic finding of copyright infringement.',
            style: TextStyle(color: Color(0xFF9BA7C7), height: 1.45),
          ),
        ],
      ),
    );
  }

  Widget _notice() => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFF21E6FF).withValues(alpha: .45)),
          color: const Color(0xFF11172A),
        ),
        child: const Row(
          children: [
            Icon(Icons.lock_outline_rounded, color: Color(0xFF21E6FF)),
            SizedBox(width: 12),
            Expanded(child: Text('READ-ONLY EVIDENCE • HUMAN REVIEW REQUIRED')),
          ],
        ),
      );

  Widget _section(String title, List<Widget> children) => Card(
        margin: const EdgeInsets.only(bottom: 12),
        child: Padding(
          padding: const EdgeInsets.only(top: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                child: Text(title, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF9BA7C7))),
              ),
              ...children,
            ],
          ),
        ),
      );

  Widget _row(String label, String value) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 7, 16, 7),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(width: 110, child: Text(label, style: const TextStyle(color: Color(0xFF9BA7C7)))),
            const SizedBox(width: 12),
            Expanded(child: SelectableText(value)),
          ],
        ),
      );
}
