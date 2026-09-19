import 'package:flutter/material.dart';

import '../../shared/widgets/info_card.dart';

class WholesalePage extends StatelessWidget {
  const WholesalePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('یافتن عمده‌فروش')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          InfoCard(
            title: 'مسیر جداگانه عمده‌فروشی',
            icon: Icons.storefront_outlined,
            child: Text(
              'این مسیر در Phase 6 منابع تأمین‌کننده، حداقل سفارش، ارسال و اطلاعات تماس عمومی را جداگانه جمع‌آوری می‌کند.',
            ),
          ),
        ],
      ),
    );
  }
}
