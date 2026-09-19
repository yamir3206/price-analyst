import 'package:flutter_test/flutter_test.dart';
import 'package:price_analyst/app/app.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

void main() {
  testWidgets('renders the search shell', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: PriceAnalystApp()));

    expect(find.text('Price Analyst'), findsOneWidget);
    expect(find.text('جستجوی قیمت'), findsOneWidget);
    expect(find.text('شروع جستجو'), findsOneWidget);
  });
}
