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

class PriceStatistics {
  const PriceStatistics({
    required this.count,
    this.currency,
    this.minimum,
    this.p25,
    this.median,
    this.p75,
    this.maximum,
    this.mean,
    this.standardDeviation,
  });

  final int count;
  final String? currency;
  final double? minimum;
  final double? p25;
  final double? median;
  final double? p75;
  final double? maximum;
  final double? mean;
  final double? standardDeviation;

  factory PriceStatistics.fromJson(Map<String, dynamic> json) {
    return PriceStatistics(
      count: json['count'] as int? ?? 0,
      currency: json['currency'] as String?,
      minimum: _doubleValue(json['minimum']),
      p25: _doubleValue(json['p25']),
      median: _doubleValue(json['median']),
      p75: _doubleValue(json['p75']),
      maximum: _doubleValue(json['maximum']),
      mean: _doubleValue(json['mean']),
      standardDeviation: _doubleValue(json['standard_deviation']),
    );
  }
}

class PriceChartPoint {
  const PriceChartPoint({
    required this.offerId,
    required this.source,
    required this.label,
    required this.amount,
    required this.classification,
  });

  final String offerId;
  final String source;
  final String label;
  final int amount;
  final String classification;

  factory PriceChartPoint.fromJson(Map<String, dynamic> json) {
    return PriceChartPoint(
      offerId: json['offer_id'] as String? ?? '',
      source: json['source'] as String? ?? 'unknown',
      label: json['label'] as String? ?? 'unknown',
      amount: json['amount'] as int? ?? 0,
      classification: json['classification'] as String? ?? 'unknown',
    );
  }
}

class PriceChart {
  const PriceChart({
    required this.currency,
    required this.points,
    this.p25,
    this.median,
    this.p75,
  });

  final String currency;
  final List<PriceChartPoint> points;
  final double? p25;
  final double? median;
  final double? p75;

  factory PriceChart.fromJson(Map<String, dynamic> json) {
    final pointJson = json['points'];
    final points = pointJson is List
        ? pointJson
            .whereType<Map<String, dynamic>>()
            .map(PriceChartPoint.fromJson)
            .toList(growable: false)
        : const <PriceChartPoint>[];
    return PriceChart(
      currency: json['currency'] as String? ?? 'UNKNOWN',
      points: points,
      p25: _doubleValue(json['p25']),
      median: _doubleValue(json['median']),
      p75: _doubleValue(json['p75']),
    );
  }
}

class Opportunity {
  const Opportunity({
    required this.offerId,
    required this.currency,
    required this.totalCost,
    required this.profit,
    required this.profitMargin,
    required this.roi,
    required this.classification,
  });

  final String offerId;
  final String currency;
  final double totalCost;
  final double profit;
  final double? profitMargin;
  final double? roi;
  final String classification;

  factory Opportunity.fromJson(Map<String, dynamic> json) {
    return Opportunity(
      offerId: json['offer_id'] as String? ?? '',
      currency: json['currency'] as String? ?? 'UNKNOWN',
      totalCost: _doubleValue(json['total_cost']) ?? 0,
      profit: _doubleValue(json['profit']) ?? 0,
      profitMargin: _doubleValue(json['profit_margin']),
      roi: _doubleValue(json['roi']),
      classification: json['classification'] as String? ?? 'below_market',
    );
  }
}

class AiAnalysisResult {
  const AiAnalysisResult({
    required this.summary,
    required this.marketAssessment,
    required this.cheapOffers,
    required this.expensiveOffers,
    required this.potentialOpportunities,
    required this.risks,
    required this.missingInformation,
    required this.facts,
    required this.inferences,
    required this.uncertainties,
    required this.confidence,
  });

  final String summary;
  final String marketAssessment;
  final List<String> cheapOffers;
  final List<String> expensiveOffers;
  final List<String> potentialOpportunities;
  final List<String> risks;
  final List<String> missingInformation;
  final List<String> facts;
  final List<String> inferences;
  final List<String> uncertainties;
  final double confidence;

  factory AiAnalysisResult.fromJson(Map<String, dynamic> json) {
    return AiAnalysisResult(
      summary: json['summary'] as String? ?? '',
      marketAssessment: json['market_assessment'] as String? ?? '',
      cheapOffers: _stringList(json['cheap_offers']),
      expensiveOffers: _stringList(json['expensive_offers']),
      potentialOpportunities: _stringList(json['potential_opportunities']),
      risks: _stringList(json['risks']),
      missingInformation: _stringList(json['missing_information']),
      facts: _stringList(json['facts']),
      inferences: _stringList(json['inferences']),
      uncertainties: _stringList(json['uncertainties']),
      confidence: _doubleValue(json['confidence']) ?? 0,
    );
  }
}

class AiAnalysisEnvelope {
  const AiAnalysisEnvelope({
    required this.status,
    this.result,
    this.datasetHash,
    this.promptVersion,
    this.model,
    this.errorCode,
    this.errorMessage,
  });

  const AiAnalysisEnvelope.notRequested()
      : status = 'not_requested',
        result = null,
        datasetHash = null,
        promptVersion = null,
        model = null,
        errorCode = null,
        errorMessage = null;

  final String status;
  final AiAnalysisResult? result;
  final String? datasetHash;
  final String? promptVersion;
  final String? model;
  final String? errorCode;
  final String? errorMessage;

  factory AiAnalysisEnvelope.fromJson(Map<String, dynamic> json) {
    final resultJson = json['result'];
    return AiAnalysisEnvelope(
      status: json['status'] as String? ?? 'not_requested',
      result: resultJson is Map<String, dynamic>
          ? AiAnalysisResult.fromJson(resultJson)
          : null,
      datasetHash: json['dataset_hash'] as String?,
      promptVersion: json['prompt_version'] as String?,
      model: json['model'] as String?,
      errorCode: json['error_code'] as String?,
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
    this.statistics,
    this.priceCharts = const [],
    this.opportunities = const [],
    this.stale = false,
    this.aiAnalysis = const AiAnalysisEnvelope.notRequested(),
  });

  final NormalizedQuery query;
  final int offerCount;
  final String collectionStatus;
  final List<SourceStatus> sourceStatuses;
  final DateTime? collectedAt;
  final PriceStatistics? statistics;
  final List<PriceChart> priceCharts;
  final List<Opportunity> opportunities;
  final bool stale;
  final AiAnalysisEnvelope aiAnalysis;

  factory SearchSnapshot.fromJson(Map<String, dynamic> json) {
    final sourceJson = json['source_statuses'];
    final statuses = sourceJson is List
        ? sourceJson
            .whereType<Map<String, dynamic>>()
            .map(SourceStatus.fromJson)
            .toList(growable: false)
        : const <SourceStatus>[];
    final localJson = json['local_analysis'];
    final local = localJson is Map<String, dynamic>
        ? localJson
        : const <String, dynamic>{};
    final chartJson = local['price_charts'];
    final charts = chartJson is List
        ? chartJson
            .whereType<Map<String, dynamic>>()
            .map(PriceChart.fromJson)
            .toList(growable: false)
        : const <PriceChart>[];
    final opportunityJson = local['opportunities'];
    final opportunities = opportunityJson is List
        ? opportunityJson
            .whereType<Map<String, dynamic>>()
            .map(Opportunity.fromJson)
            .toList(growable: false)
        : const <Opportunity>[];
    final statisticsJson = json['statistics'];
    final aiJson = json['ai_analysis'];

    return SearchSnapshot(
      query: NormalizedQuery.fromJson(
        (json['query'] as Map<String, dynamic>?) ?? const {},
      ),
      offerCount: (json['offers'] as List?)?.length ?? 0,
      collectionStatus: json['collection_status'] as String? ?? 'unknown',
      sourceStatuses: statuses,
      collectedAt: DateTime.tryParse(json['collected_at'] as String? ?? ''),
      statistics: statisticsJson is Map<String, dynamic>
          ? PriceStatistics.fromJson(statisticsJson)
          : null,
      priceCharts: charts,
      opportunities: opportunities,
      stale: json['stale'] as bool? ?? false,
      aiAnalysis: aiJson is Map<String, dynamic>
          ? AiAnalysisEnvelope.fromJson(aiJson)
          : const AiAnalysisEnvelope.notRequested(),
    );
  }

  int get availableSourceCount =>
      sourceStatuses.where((source) => source.adapterConfigured).length;
}

List<String> _stringList(dynamic value) => value is List
    ? value.whereType<String>().toList(growable: false)
    : const <String>[];

double? _doubleValue(dynamic value) => value is num ? value.toDouble() : null;
