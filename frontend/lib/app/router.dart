import 'package:go_router/go_router.dart';

import '../features/ai_analysis/ai_analysis_page.dart';
import '../features/analysis/analysis_page.dart';
import '../features/opportunity/opportunity_page.dart';
import '../features/results/results_page.dart';
import '../features/search/search_page.dart';
import '../features/settings/settings_page.dart';
import '../features/wholesale/wholesale_page.dart';

final appRouter = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(path: '/', builder: (context, state) => const SearchPage()),
    GoRoute(path: '/results', builder: (context, state) => const ResultsPage()),
    GoRoute(
      path: '/analysis',
      builder: (context, state) => const AnalysisPage(),
    ),
    GoRoute(
      path: '/ai-analysis',
      builder: (context, state) => const AiAnalysisPage(),
    ),
    GoRoute(
      path: '/opportunity',
      builder: (context, state) => const OpportunityPage(),
    ),
    GoRoute(
      path: '/wholesale',
      builder: (context, state) => const WholesalePage(),
    ),
    GoRoute(
      path: '/settings',
      builder: (context, state) => const SettingsPage(),
    ),
  ],
);
