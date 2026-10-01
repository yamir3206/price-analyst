import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models/search_models.dart';
import '../../core/state/search_controller.dart';
import '../../shared/widgets/info_card.dart';

class OpportunityPage extends ConsumerWidget {
  const OpportunityPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final snapshot = ref.watch(searchControllerProvider).snapshot;
    final opportunities = snapshot?.opportunities ?? const <Opportunity>[];
    return Scaffold(
      appBar: AppBar(title: const Text('فرصت خرید و فروش')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          InfoCard(
            title: 'محاسبه‌گر قطعی',
            icon: Icons.trending_up,
            child: opportunities.isEmpty
                ? const Text(
                    'فرصت مثبت قابل مقایسه‌ای پیدا نشد. نتیجه به‌صورت محافظه‌کارانه با میانه بازار محاسبه می‌شود.',
                  )
                : Column(
                    children: opportunities
                        .map((opportunity) => _OpportunityTile(opportunity: opportunity))
                        .toList(growable: false),
                  ),
          ),
          const SizedBox(height: 12),
          const InfoCard(
            title: 'فرض محاسبه',
            child: Text(
              'قیمت فروش مورد انتظار برابر با میانه قیمت‌های قابل مقایسه در همان ارز است؛ این مقدار تضمین فروش آینده نیست.',
            ),
          ),
        ],
      ),
    );
  }
}

class _OpportunityTile extends StatelessWidget {
  const _OpportunityTile({required this.opportunity});

  final Opportunity opportunity;

  @override
  Widget build(BuildContext context) {
    final margin = opportunity.profitMargin == null
        ? '—'
        : '${(opportunity.profitMargin! * 100).toStringAsFixed(1)}%';
    final roi = opportunity.roi == null
        ? '—'
        : '${(opportunity.roi! * 100).toStringAsFixed(1)}%';
    return ListTile(
      contentPadding: EdgeInsets.zero,
      title: Text('پیشنهاد ${opportunity.offerId}'),
      subtitle: Text('وضعیت: ${opportunity.classification} · ارز: ${opportunity.currency}'),
      trailing: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text('سود ${opportunity.profit.toStringAsFixed(0)}'),
          Text('حاشیه $margin · بازده $roi'),
        ],
      ),
    );
  }
}
