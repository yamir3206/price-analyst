import 'package:flutter/material.dart';

import '../../shared/widgets/info_card.dart';

class AiAnalysisPage extends StatelessWidget {
  const AiAnalysisPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('تحلیل Gemini')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          InfoCard(
            title: 'لایه تفسیر اختیاری',
            icon: Icons.auto_awesome_outlined,
            child: Text(
              'Gemini فقط پس از جمع‌آوری، نرمال‌سازی و محاسبه محلی داده‌ها نظر تحلیلی می‌دهد. در صورت قطعی بودن این بخش، نتایج قطعی همچنان قابل استفاده هستند.',
            ),
          ),
          SizedBox(height: 12),
          InfoCard(
            title: 'وضعیت',
            child: Text('در Phase 5 به سرویس تحلیل ساختاریافته متصل می‌شود.'),
          ),
        ],
      ),
    );
  }
}
