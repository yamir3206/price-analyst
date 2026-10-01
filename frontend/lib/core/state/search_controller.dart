import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../models/search_models.dart';

class SearchState {
  const SearchState({
    this.isLoading = false,
    this.isAnalyzing = false,
    this.snapshot,
    this.errorMessage,
  });

  final bool isLoading;
  final bool isAnalyzing;
  final SearchSnapshot? snapshot;
  final String? errorMessage;

  SearchState copyWith({
    bool? isLoading,
    bool? isAnalyzing,
    SearchSnapshot? snapshot,
    String? errorMessage,
    bool clearError = false,
  }) {
    return SearchState(
      isLoading: isLoading ?? this.isLoading,
      isAnalyzing: isAnalyzing ?? this.isAnalyzing,
      snapshot: snapshot ?? this.snapshot,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }
}

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

final searchControllerProvider =
    StateNotifierProvider<SearchController, SearchState>((ref) {
  return SearchController(ref.watch(apiClientProvider));
});

class SearchController extends StateNotifier<SearchState> {
  SearchController(this._apiClient) : super(const SearchState());

  final ApiClient _apiClient;

  Future<bool> search(String query) async {
    final trimmed = query.trim();
    if (trimmed.isEmpty) {
      state = const SearchState(errorMessage: 'یک نام محصول وارد کنید.');
      return false;
    }

    state = const SearchState(isLoading: true);
    try {
      final snapshot = await _apiClient.search(trimmed);
      state = SearchState(snapshot: snapshot);
      return true;
    } on ApiException catch (error) {
      state = SearchState(errorMessage: error.message);
      return false;
    } on Object {
      state = const SearchState(
        errorMessage: 'ارتباط با سرور برقرار نشد. دوباره تلاش کنید.',
      );
      return false;
    }
  }

  Future<bool> analyze() async {
    final current = state.snapshot;
    if (current == null) {
      state = const SearchState(errorMessage: 'ابتدا یک جستجو انجام دهید.');
      return false;
    }

    state = state.copyWith(isAnalyzing: true, clearError: true);
    try {
      final snapshot = await _apiClient.analyze(current.query.original);
      state = state.copyWith(
        isAnalyzing: false,
        snapshot: snapshot,
        clearError: true,
      );
      return true;
    } on ApiException catch (error) {
      state = state.copyWith(isAnalyzing: false, errorMessage: error.message);
      return false;
    } on Object {
      state = state.copyWith(
        isAnalyzing: false,
        errorMessage: 'ارتباط با سرویس تحلیل برقرار نشد.',
      );
      return false;
    }
  }
}
