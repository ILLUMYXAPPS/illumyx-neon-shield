import 'package:flutter/material.dart';

class InvestigationSummary {
  const InvestigationSummary({
    required this.id,
    required this.evidenceCount,
    required this.pendingReviewCount,
    required this.highestConfidence,
  });

  final String id;
  final int evidenceCount;
  final int pendingReviewCount;
  final double highestConfidence;
}

class ResultsCentreView extends StatefulWidget {
  const ResultsCentreView({super.key, this.investigations = const []});

  final List<InvestigationSummary> investigations;

  @override
  State<ResultsCentreView> createState() => _ResultsCentreViewState();
}

class _ResultsCentreViewState extends State<ResultsCentreView> {
  String query = '';

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
