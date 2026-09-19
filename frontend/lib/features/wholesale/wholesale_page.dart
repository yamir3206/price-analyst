import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models/wholesale_models.dart';
import '../../core/state/wholesale_controller.dart';
import '../../shared/widgets/info_card.dart';

class WholesalePage extends ConsumerStatefulWidget {
  const WholesalePage({super.key});

  @override
  ConsumerState<WholesalePage> createState() => _WholesalePageState();
}

class _WholesalePageState extends ConsumerState<WholesalePage> {
  final _queryController = TextEditingController();

  @override
  void dispose() {
    _queryController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    await ref
        .read(wholesaleControllerProvider.notifier)
        .search(_queryController.text);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(wholesaleControllerProvider);
    final snapshot = state.snapshot;
    return Scaffold(
      appBar: AppBar(title: const Text('یافتن عمده‌فروش')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const InfoCard(
            title: 'مسیر جداگانه عمده‌فروشی',
            icon: Icons.storefront_outlined,
            child: Text(
              'این بخش منابع تأمین‌کننده، حداقل سفارش، ارسال و اطلاعات عمومی تماس را جدا از نتایج خرده‌فروشی نگه می‌دارد.',
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _queryController,
            textInputAction: TextInputAction.search,
            onSubmitted: (_) => _submit(),
            decoration: const InputDecoration(
              labelText: 'نام محصول',
              hintText: 'مثلاً لوازم جانبی موبایل',
              prefixIcon: Icon(Icons.search),
            ),
          ),
          const SizedBox(height: 8),
          FilledButton.icon(
            onPressed: state.isLoading ? null : _submit,
            icon: state.isLoading
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.search),
            label: Text(state.isLoading ? 'در حال جستجو...' : 'جستجوی عمده‌فروشی'),
          ),
          if (state.errorMessage != null) ...[
            const SizedBox(height: 12),
            Text(
              state.errorMessage!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          if (snapshot != null) ...[
            const SizedBox(height: 16),
            _SnapshotSummary(snapshot: snapshot),
            const SizedBox(height: 12),
            if (snapshot.listings.isEmpty)
              const InfoCard(
                title: 'نتیجه‌ای پیدا نشد',
                child: Text(
                  'منبع عمده‌فروشی فعال نیست یا برای این جستجو داده عمومی در دسترس نبود.',
                ),
              )
            else
              ...snapshot.listings.map((listing) => _ListingCard(listing)),
          ],
        ],
      ),
    );
  }
}

class _SnapshotSummary extends StatelessWidget {
  const _SnapshotSummary({required this.snapshot});

  final WholesaleSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return InfoCard(
      title: 'وضعیت جمع‌آوری: ${snapshot.collectionStatus}',
      icon: Icons.fact_check_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('تعداد فهرست‌ها: ${snapshot.listings.length}'),
          if (snapshot.stale) const Text('برخی داده‌ها از آخرین snapshot استفاده می‌کنند.'),
          ...snapshot.sourceStatuses.map(
            (source) => Text(
              '${source.source}: ${source.state} (${source.listingCount})',
            ),
          ),
        ],
      ),
    );
  }
}

class _ListingCard extends StatelessWidget {
  const _ListingCard(this.listing);

  final WholesaleListing listing;

  @override
  Widget build(BuildContext context) {
    final price = listing.unitPrice;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: InfoCard(
        title: listing.title,
        icon: Icons.inventory_2_outlined,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('منبع: ${listing.source}'),
            if (listing.supplierName != null) Text('تأمین‌کننده: ${listing.supplierName}'),
            if (listing.minimumOrderQuantity != null)
              Text('حداقل سفارش: ${listing.minimumOrderQuantity}'),
            if (price != null) Text('قیمت واحد: ${price.amount} ${price.currency}'),
            if (listing.location != null) Text('موقعیت: ${listing.location}'),
            if (listing.shippingInformation != null)
              Text('ارسال: ${listing.shippingInformation}'),
            if (listing.publicContact != null)
              Text('تماس عمومی: ${listing.publicContact}'),
            if (listing.productUrl != null) Text('نشانی عمومی: ${listing.productUrl}'),
          ],
        ),
      ),
    );
  }
}
