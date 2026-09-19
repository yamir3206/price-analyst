import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../models/wholesale_models.dart';
import 'search_controller.dart';

class WholesaleState {
  const WholesaleState({
    this.isLoading = false,
    this.snapshot,
    this.errorMessage,
  });

  final bool isLoading;
  final WholesaleSnapshot? snapshot;
  final String? errorMessage;
}

final wholesaleControllerProvider =
    StateNotifierProvider<WholesaleController, WholesaleState>((ref) {
  return WholesaleController(ref.watch(apiClientProvider));
});

class WholesaleController extends StateNotifier<WholesaleState> {
  WholesaleController(this._apiClient) : super(const WholesaleState());

  final ApiClient _apiClient;

  Future<bool> search(String query) async {
    final trimmed = query.trim();
    if (trimmed.isEmpty) {
      state = const WholesaleState(errorMessage: 'یک محصول برای عمده‌فروشی وارد کنید.');
      return false;
    }

    state = const WholesaleState(isLoading: true);
    try {
      final snapshot = await _apiClient.wholesaleSearch(trimmed);
      state = WholesaleState(snapshot: snapshot);
      return true;
    } on ApiException catch (error) {
      state = WholesaleState(errorMessage: error.message);
      return false;
    } on Object {
      state = const WholesaleState(
        errorMessage: 'ارتباط با سرویس عمده‌فروشی برقرار نشد.',
      );
      return false;
    }
  }
}
