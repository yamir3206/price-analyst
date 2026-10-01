import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/state/search_controller.dart';
import '../../shared/widgets/info_card.dart';

class ResultsPage extends ConsumerWidget {
  const ResultsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(searchControllerProvider);
    final snapshot = state.snapshot;
    return Scaffold(
      appBar: AppBar(title: const Text('نتایج جمع‌آوری')),
      body: snapshot == null
          ? Center(
              child: FilledButton(
                onPressed: () => context.go('/'),
                child: const Text('بازگشت به جستجو'),
              ),
            )
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                InfoCard(
                  title: 'داده قطعی',
                  icon: Icons.verified_outlined,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('محصول: ${snapshot.query.normalizedText}'),
                      const SizedBox(height: 6),
                      Text('تعداد پیشنهادها: ${snapshot.offerCount}'),
                      Text('منابع در دسترس: ${snapshot.availableSourceCount}'),
                      Text('وضعیت: ${snapshot.collectionStatus}'),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                InfoCard(
                  title: 'وضعیت منابع',
                  icon: Icons.hub_outlined,
                  child: Column(
                    children: snapshot.sourceStatuses
                        .map(
                          (source) => ListTile(
                            dense: true,
                            contentPadding: EdgeInsets.zero,
                            title: Text(source.source),
                            subtitle: source.errorMessage == null
                                ? null
                                : Text(source.errorMessage!),
                            trailing: Text(source.state),
                          ),
                        )
                        .toList(growable: false),
                  ),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    OutlinedButton.icon(
                      onPressed: () => context.push('/analysis'),
                      icon: const Icon(Icons.analytics_outlined),
                      label: const Text('تحلیل قیمت'),
                    ),
                    OutlinedButton.icon(
                      onPressed: () => context.push('/ai-analysis'),
                      icon: const Icon(Icons.auto_awesome_outlined),
                      label: const Text('تحلیل AI'),
                    ),
                    OutlinedButton.icon(
                      onPressed: () => context.push('/opportunity'),
                      icon: const Icon(Icons.trending_up),
                      label: const Text('فرصت خرید و فروش'),
                    ),
                  ],
                ),
              ],
            ),
    );
  }
}
