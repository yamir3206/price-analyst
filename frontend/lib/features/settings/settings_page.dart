import 'package:flutter/material.dart';

import '../../shared/widgets/info_card.dart';

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('تنظیمات')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          InfoCard(
            title: 'اتصال و منابع',
            icon: Icons.tune,
            child: Text(
              'آدرس backend از طریق API_BASE_URL تنظیم می‌شود. کلیدهای Gemini در frontend ذخیره نمی‌شوند.',
            ),
          ),
          SizedBox(height: 12),
          InfoCard(
            title: 'زبان',
            child: Text('رابط کاربری Phase 1 با چیدمان RTL فارسی آماده شده است.'),
          ),
        ],
      ),
    );
  }
}
