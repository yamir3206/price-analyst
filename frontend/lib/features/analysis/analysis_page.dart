import 'package:flutter/material.dart';

import '../../shared/widgets/info_card.dart';

class AnalysisPage extends StatelessWidget {
  const AnalysisPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('تحلیل قیمت محلی')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          InfoCard(
            title: 'آمار قطعی',
            icon: Icons.calculate_outlined,
            child: Text(
              'پس از فعال شدن منابع، حداقل، حداکثر، میانگین، میانه، صدک‌ها و پراکندگی در این بخش نمایش داده می‌شوند.',
            ),
          ),
          SizedBox(height: 12),
          InfoCard(
            title: 'نمودار توزیع',
            icon: Icons.bar_chart_outlined,
            child: Text(
              'نمودار توزیع و مقایسه منابع به‌صورت محلی از مجموعه کامل داده ساخته خواهد شد.',
            ),
          ),
        ],
      ),
    );
  }
}
