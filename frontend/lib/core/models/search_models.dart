class NormalizedQuery {
  const NormalizedQuery({
    required this.original,
    required this.normalizedText,
    this.brand,
    this.model,
    this.capacity,
    this.color,
  });

  final String original;
  final String normalizedText;
  final String? brand;
  final String? model;
  final String? capacity;
  final String? color;

  factory NormalizedQuery.fromJson(Map<String, dynamic> json) {
    return NormalizedQuery(
      original: json['original'] as String? ?? '',
      normalizedText: json['normalized_text'] as String? ?? '',
      brand: json['brand'] as String?,
      model: json['model'] as String?,
      capacity: json['capacity'] as String?,
      color: json['color'] as String?,
    );
  }
}

class SourceStatus {
  const SourceStatus({
    required this.source,
    required this.state,
    required this.adapterConfigured,
    this.errorMessage,
  });

  final String source;
  final String state;
  final bool adapterConfigured;
  final String? errorMessage;

  factory SourceStatus.fromJson(Map<String, dynamic> json) {
    return SourceStatus(
      source: json['source'] as String? ?? 'unknown',
      state: json['state'] as String? ?? 'unknown',
      adapterConfigured: json['adapter_configured'] as bool? ?? false,
      errorMessage: json['error_message'] as String?,
    );
  }
}

class SearchSnapshot {
  const SearchSnapshot({
    required this.query,
    required this.offerCount,
    required this.collectionStatus,
    required this.sourceStatuses,
    required this.collectedAt,
  });

  final NormalizedQuery query;
  final int offerCount;
  final String collectionStatus;
  final List<SourceStatus> sourceStatuses;
  final DateTime? collectedAt;

  factory SearchSnapshot.fromJson(Map<String, dynamic> json) {
    final sourceJson = json['source_statuses'];
    final statuses = sourceJson is List
        ? sourceJson
            .whereType<Map<String, dynamic>>()
            .map(SourceStatus.fromJson)
            .toList(growable: false)
        : const <SourceStatus>[];

    return SearchSnapshot(
      query: NormalizedQuery.fromJson(
        (json['query'] as Map<String, dynamic>?) ?? const {},
      ),
      offerCount: (json['offers'] as List?)?.length ?? 0,
      collectionStatus: json['collection_status'] as String? ?? 'unknown',
      sourceStatuses: statuses,
      collectedAt: DateTime.tryParse(json['collected_at'] as String? ?? ''),
    );
  }

  int get availableSourceCount =>
      sourceStatuses.where((source) => source.adapterConfigured).length;
}
