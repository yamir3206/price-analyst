import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models/search_models.dart';
import '../../core/state/search_controller.dart';
import '../../shared/widgets/info_card.dart';

class AiAnalysisPage extends ConsumerWidget {
  const AiAnalysisPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(searchControllerProvider);
    final snapshot = state.snapshot;
    final analysis = snapshot?.aiAnalysis;
    final result = analysis?.result;

    return Scaffold(
      appBar: AppBar(title: const Text('تحلیل Gemini')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const InfoCard(
            title: 'لایه تفسیر اختیاری',
            icon: Icons.auto_awesome_outlined,
            child: Text(
              'Gemini فقط پس از جمع‌آوری، نرمال‌سازی و محاسبه محلی داده‌ها نظر می‌دهد. داده قطعی بازار مستقل از این بخش باقی می‌ماند.',
            ),
          ),
          const SizedBox(height: 12),
          if (snapshot == null)
            const InfoCard(
              title: 'داده‌ای برای تحلیل نیست',
              child: Text('ابتدا یک جستجو انجام دهید و سپس این صفحه را باز کنید.'),
            )
          else ...[
            FilledButton.icon(
              onPressed: state.isAnalyzing
                  ? null
                  : () => ref.read(searchControllerProvider.notifier).analyze(),
              icon: state.isAnalyzing
                  ? const SizedBox.square(
                      dimension: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.auto_awesome),
              label: Text(
                state.isAnalyzing ? 'در حال تحلیل...' : 'درخواست تحلیل ساختاریافته',
              ),
            ),
            const SizedBox(height: 12),
            _StatusCard(analysis: analysis!),
            if (result != null) ...[
              const SizedBox(height: 12),
              _ResultCards(result: result),
            ],
          ],
          if (state.errorMessage != null) ...[
            const SizedBox(height: 12),
            Text(
              state.errorMessage!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
        ],
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({required this.analysis});

  final AiAnalysisEnvelope analysis;

  @override
  Widget build(BuildContext context) {
    final hash = analysis.datasetHash;
    final status = switch (analysis.status) {
      'completed' => 'تحلیل آماده است',
      'cached' => 'تحلیل از حافظه نهان خوانده شد',
      'disabled' => 'Gemini در backend فعال نیست',
      'invalid_response' => 'پاسخ Gemini ساختار معتبر نداشت',
      'failed' => 'تحلیل در دسترس نیست',
      _ => 'هنوز تحلیلی درخواست نشده است',
    };
    return InfoCard(
      title: 'وضعیت: $status',
      icon: Icons.info_outline,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (analysis.errorMessage != null) Text(analysis.errorMessage!),
          if (analysis.model != null) Text('مدل: ${analysis.model}'),
          if (hash != null)
            Text(
              'شناسه داده فشرده: ${hash.substring(0, hash.length < 8 ? hash.length : 8)}…',
            ),
        ],
      ),
    );
  }
}

class _ResultCards extends StatelessWidget {
  const _ResultCards({required this.result});

  final AiAnalysisResult result;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        InfoCard(
          title: 'خلاصه و ارزیابی بازار',
          icon: Icons.summarize_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(result.summary),
              if (result.marketAssessment.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(result.marketAssessment),
              ],
              const SizedBox(height: 8),
              Text('اعتماد مدل: ${(result.confidence * 100).round()}٪'),
            ],
          ),
        ),
        const SizedBox(height: 12),
        _ListCard(title: 'واقعیت‌های مشاهده‌شده', values: result.facts),
        const SizedBox(height: 12),
        _ListCard(title: 'استنباط‌ها', values: result.inferences),
        const SizedBox(height: 12),
        _ListCard(title: 'عدم قطعیت‌ها و داده‌های ناقص', values: [
          ...result.uncertainties,
          ...result.missingInformation,
        ]),
        const SizedBox(height: 12),
        _ListCard(title: 'ریسک‌ها', values: result.risks),
        const SizedBox(height: 12),
        _ListCard(title: 'پیشنهادهای ارزان‌تر', values: result.cheapOffers),
        const SizedBox(height: 12),
        _ListCard(title: 'پیشنهادهای گران‌تر', values: result.expensiveOffers),
        const SizedBox(height: 12),
        _ListCard(
          title: 'فرصت‌های بالقوه',
          values: result.potentialOpportunities,
        ),
      ],
    );
  }
}

class _ListCard extends StatelessWidget {
  const _ListCard({required this.title, required this.values});

  final String title;
  final List<String> values;

  @override
  Widget build(BuildContext context) {
    return InfoCard(
      title: title,
      child: values.isEmpty
          ? const Text('موردی گزارش نشده است.')
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: values
                  .map((value) => Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Text('• $value'),
                      ))
                  .toList(growable: false),
            ),
    );
  }
}
