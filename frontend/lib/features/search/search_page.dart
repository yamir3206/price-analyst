import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/state/search_controller.dart';

class SearchPage extends ConsumerStatefulWidget {
  const SearchPage({super.key});

  @override
  ConsumerState<SearchPage> createState() => _SearchPageState();
}

class _SearchPageState extends ConsumerState<SearchPage> {
  final _queryController = TextEditingController();

  @override
  void dispose() {
    _queryController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final didSucceed =
        await ref.read(searchControllerProvider.notifier).search(_queryController.text);
    if (didSucceed && mounted) {
      context.go('/results');
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(searchControllerProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Price Analyst'),
        actions: [
          IconButton(
            tooltip: 'تنظیمات',
            onPressed: () => context.push('/settings'),
            icon: const Icon(Icons.settings_outlined),
          ),
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: ListView(
            padding: const EdgeInsets.all(24),
            children: [
              Text(
                'جستجوی قیمت',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 8),
              const Text(
                'نام محصول را وارد کنید تا داده‌های واقعی بازار جمع‌آوری و به‌صورت محلی تحلیل شوند.',
              ),
              const SizedBox(height: 24),
              TextField(
                controller: _queryController,
                textInputAction: TextInputAction.search,
                onSubmitted: (_) => _submit(),
                decoration: const InputDecoration(
                  labelText: 'نام محصول',
                  hintText: 'مثلاً Samsung Galaxy S24 Ultra 256GB',
                  prefixIcon: Icon(Icons.search),
                ),
              ),
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: state.isLoading ? null : _submit,
                icon: state.isLoading
                    ? const SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.search),
                label: const Text('شروع جستجو'),
              ),
              if (state.errorMessage != null) ...[
                const SizedBox(height: 16),
                Text(
                  state.errorMessage!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
              const SizedBox(height: 32),
              const _PipelineSummary(),
            ],
          ),
        ),
      ),
    );
  }
}

class _PipelineSummary extends StatelessWidget {
  const _PipelineSummary();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('روند تحلیل', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            const Text('۱. جمع‌آوری قطعی از منابع'),
            const Text('۲. نرمال‌سازی و حذف داده‌های تکراری'),
            const Text('۳. محاسبه محلی شاخص‌های قیمت'),
            const Text('۴. تحلیل اختیاری Gemini'),
          ],
        ),
      ),
    );
  }
}
