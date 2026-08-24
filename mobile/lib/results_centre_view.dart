import 'package:flutter/material.dart';

import 'evidence_detail_view.dart';

class InvestigationSummary {
  const InvestigationSummary({
    required this.id,
    required this.evidenceCount,
    required this.pendingReviewCount,
    required this.highestConfidence,
    this.evidence = const [],
  });

  final String id;
  final int evidenceCount;
  final int pendingReviewCount;
  final double highestConfidence;
  final List<EvidenceDetail> evidence;
}

class ResultsCentreView extends StatefulWidget {
  const ResultsCentreView({super.key, this.investigations = const []});

  final List<InvestigationSummary> investigations;

  @override
  State<ResultsCentreView> createState() => _ResultsCentreViewState();
}

class _ResultsCentreViewState extends State<ResultsCentreView> {
  String query = '';

  void _openInvestigation(InvestigationSummary investigation) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => InvestigationEvidenceView(
          investigationId: investigation.id,
          evidence: investigation.evidence,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final needle = query.trim().toLowerCase();
    final visible = widget.investigations.where((item) {
      return needle.isEmpty || item.id.toLowerCase().contains(needle);
    }).toList();

    return Scaffold(
      appBar: AppBar(title: const Text('Results Centre')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 12, 18, 8),
            child: TextField(
              decoration: const InputDecoration(
                labelText: 'Search investigations',
                prefixIcon: Icon(Icons.search_rounded),
                border: OutlineInputBorder(),
              ),
              onChanged: (value) => setState(() => query = value),
            ),
          ),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 18, vertical: 8),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'READ-ONLY • HUMAN REVIEW REQUIRED',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
              ),
            ),
          ),
          Expanded(
            child: visible.isEmpty
                ? const Center(child: Text('No investigations found.'))
                : ListView.builder(
                    padding: const EdgeInsets.all(18),
                    itemCount: visible.length,
                    itemBuilder: (context, index) {
                      final item = visible[index];
                      return Card(
                        child: ListTile(
                          leading: const Icon(Icons.folder_copy_outlined),
                          title: Text(item.id),
                          subtitle: Text(
                            '${item.evidenceCount} evidence record(s) • '
                            '${item.pendingReviewCount} pending review • '
                            'highest ${item.highestConfidence.toStringAsFixed(1)}%',
                          ),
                          trailing: const Icon(Icons.chevron_right_rounded),
                          onTap: () => _openInvestigation(item),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

class InvestigationEvidenceView extends StatelessWidget {
  const InvestigationEvidenceView({
    super.key,
    required this.investigationId,
    required this.evidence,
  });

  final String investigationId;
  final List<EvidenceDetail> evidence;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(investigationId)),
      body: evidence.isEmpty
          ? const Center(child: Text('No evidence records available.'))
          : ListView.builder(
              padding: const EdgeInsets.all(18),
              itemCount: evidence.length,
              itemBuilder: (context, index) {
                final item = evidence[index];
                return Card(
                  child: ListTile(
                    leading: const Icon(Icons.receipt_long_outlined),
                    title: Text(item.evidenceId),
                    subtitle: Text(
                      '${item.matchType} • ${item.confidence.toStringAsFixed(1)}% • ${item.reviewStatus}',
                    ),
                    trailing: const Icon(Icons.chevron_right_rounded),
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => EvidenceDetailView(evidence: item),
                      ),
                    ),
                  ),
                );
              },
            ),
    );
  }
}
