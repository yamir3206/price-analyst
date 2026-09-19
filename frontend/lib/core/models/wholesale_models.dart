class WholesaleMoney {
  const WholesaleMoney({required this.amount, required this.currency});

  final int amount;
  final String currency;

  factory WholesaleMoney.fromJson(Map<String, dynamic> json) {
    return WholesaleMoney(
      amount: json['amount'] as int? ?? 0,
      currency: json['currency'] as String? ?? 'UNKNOWN',
    );
  }
}

class WholesaleListing {
  const WholesaleListing({
    required this.listingId,
    required this.source,
    required this.title,
    required this.observedAt,
    this.supplierName,
    this.minimumOrderQuantity,
    this.unitPrice,
    this.productUrl,
    this.shippingInformation,
    this.location,
    this.publicContact,
    this.availability = 'unknown',
    this.condition = 'unknown',
  });

  final String listingId;
  final String source;
  final String title;
  final DateTime? observedAt;
  final String? supplierName;
  final int? minimumOrderQuantity;
  final WholesaleMoney? unitPrice;
  final String? productUrl;
  final String? shippingInformation;
  final String? location;
  final String? publicContact;
  final String availability;
  final String condition;

  factory WholesaleListing.fromJson(Map<String, dynamic> json) {
    final priceJson = json['unit_price'];
    return WholesaleListing(
      listingId: json['listing_id'] as String? ?? '',
      source: json['source'] as String? ?? 'unknown',
      title: json['title'] as String? ?? '',
      observedAt: DateTime.tryParse(json['observed_at'] as String? ?? ''),
      supplierName: json['supplier_name'] as String?,
      minimumOrderQuantity: json['minimum_order_quantity'] as int?,
      unitPrice: priceJson is Map<String, dynamic>
          ? WholesaleMoney.fromJson(priceJson)
          : null,
      productUrl: json['product_url'] as String?,
      shippingInformation: json['shipping_information'] as String?,
      location: json['location'] as String?,
      publicContact: json['public_contact'] as String?,
      availability: json['availability'] as String? ?? 'unknown',
      condition: json['condition'] as String? ?? 'unknown',
    );
  }
}

class WholesaleSourceStatus {
  const WholesaleSourceStatus({
    required this.source,
    required this.state,
    required this.adapterConfigured,
    required this.listingCount,
    this.staleDataAvailable = false,
    this.errorMessage,
  });

  final String source;
  final String state;
  final bool adapterConfigured;
  final int listingCount;
  final bool staleDataAvailable;
  final String? errorMessage;

  factory WholesaleSourceStatus.fromJson(Map<String, dynamic> json) {
    return WholesaleSourceStatus(
      source: json['source'] as String? ?? 'unknown',
      state: json['state'] as String? ?? 'unknown',
      adapterConfigured: json['adapter_configured'] as bool? ?? false,
      listingCount: json['listing_count'] as int? ?? 0,
      staleDataAvailable: json['stale_data_available'] as bool? ?? false,
      errorMessage: json['error_message'] as String?,
    );
  }
}

class WholesaleSnapshot {
  const WholesaleSnapshot({
    required this.query,
    required this.listings,
    required this.sourceStatuses,
    required this.collectionStatus,
    required this.collectedAt,
    this.stale = false,
  });

  final String query;
  final List<WholesaleListing> listings;
  final List<WholesaleSourceStatus> sourceStatuses;
  final String collectionStatus;
  final DateTime? collectedAt;
  final bool stale;

  factory WholesaleSnapshot.fromJson(Map<String, dynamic> json) {
    final queryJson = json['query'];
    final sourceJson = json['source_statuses'];
    final listingJson = json['listings'];
    return WholesaleSnapshot(
      query: queryJson is Map<String, dynamic>
          ? queryJson['normalized_text'] as String? ?? ''
          : '',
      listings: listingJson is List
          ? listingJson
              .whereType<Map<String, dynamic>>()
              .map(WholesaleListing.fromJson)
              .toList(growable: false)
          : const <WholesaleListing>[],
      sourceStatuses: sourceJson is List
          ? sourceJson
              .whereType<Map<String, dynamic>>()
              .map(WholesaleSourceStatus.fromJson)
              .toList(growable: false)
          : const <WholesaleSourceStatus>[],
      collectionStatus: json['collection_status'] as String? ?? 'unknown',
      collectedAt: DateTime.tryParse(json['collected_at'] as String? ?? ''),
      stale: json['stale'] as bool? ?? false,
    );
  }
}
