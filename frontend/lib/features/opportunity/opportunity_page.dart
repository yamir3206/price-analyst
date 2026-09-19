import 'package:flutter/material.dart';

import '../../shared/widgets/info_card.dart';

class OpportunityPage extends StatelessWidget {
  const OpportunityPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('فرصت خرید و فروش')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          InfoCard(
            title: 'محاسبه‌گر قطعی',
            icon: Icons.trending_up,
            child: Text(
              'قیمت خرید، فروش مورد انتظار، ارسال و کارمزدها در backend محاسبه می‌شوند و فرض‌ها در کنار نتیجه نمایش داده خواهند شد.',
            ),
          ),
        ],
      ),
    );
  }
}
