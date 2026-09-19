import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models/search_models.dart';
import '../../core/state/search_controller.dart';
import '../../shared/widgets/info_card.dart';

class AnalysisPage extends ConsumerWidget {
  const AnalysisPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final snapshot = ref.watch(searchControllerProvider).snapshot;
    if (snapshot == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('تحلیل قیمت محلی')),
        body: const Center(child: Text('ابتدا یک جستجو انجام دهید.')),
      );
    }

    final statistics = snapshot.statistics;
    return Scaffold(
      appBar: AppBar(title: const Text('تحلیل قیمت محلی')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          InfoCard(
            title: 'آمار قطعی',
            icon: Icons.calculate_outlined,
            child: statistics == null
                ? const Text(
                    'برای این نتیجه، قیمت‌های قابل مقایسه با ارز مشخص وجود ندارد.',
                  )
                : _StatisticsView(statistics: statistics),
          ),
          const SizedBox(height: 12),
          ...snapshot.priceCharts.map(
            (chart) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: InfoCard(
                title: 'توزیع قیمت ${chart.currency}',
                icon: Icons.bar_chart_outlined,
                child: _ChartView(chart: chart),
              ),
            ),
          ),
          if (snapshot.stale)
            const InfoCard(
              title: 'هشدار داده',
              icon: Icons.warning_amber_outlined,
              child: Text('بخشی از این تحلیل از آخرین داده ذخیره‌شده استفاده می‌کند.'),
            ),
        ],
      ),
    );
  }
}

class _StatisticsView extends StatelessWidget {
  const _StatisticsView({required this.statistics});

  final PriceStatistics statistics;

  @override
  Widget build(BuildContext context) {
    final values = <String, double?>{
      'کمینه': statistics.minimum,
      'صدک ۲۵': statistics.p25,
      'میانه': statistics.median,
      'صدک ۷۵': statistics.p75,
      'بیشینه': statistics.maximum,
      'میانگین': statistics.mean,
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('تعداد مقایسه‌پذیر: ${statistics.count}'),
        Text('ارز: ${statistics.currency ?? 'نامشخص'}'),
        const SizedBox(height: 12),
        Wrap(
          spacing: 16,
          runSpacing: 10,
          children: values.entries
              .map((entry) => Text('${entry.key}: ${_formatAmount(entry.value)}'))
              .toList(growable: false),
        ),
      ],
    );
  }
}

class _ChartView extends StatelessWidget {
  const _ChartView({required this.chart});

  final PriceChart chart;

  @override
  Widget build(BuildContext context) {
    if (chart.points.isEmpty) {
      return const Text('نقطه‌ای برای نمایش وجود ندارد.');
    }
    final maximum = chart.points.fold<int>(
      0,
      (current, point) => point.amount > current ? point.amount : current,
    );
    return Column(
      children: chart.points
          .map(
            (point) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 5),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${point.label} · ${_formatAmount(point.amount.toDouble())}'),
                  const SizedBox(height: 4),
                  LinearProgressIndicator(
                    value: maximum == 0 ? 0 : point.amount / maximum,
                    minHeight: 8,
                  ),
                ],
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

String _formatAmount(double? amount) {
  if (amount == null) return '—';
  return amount.round().toString();
}
