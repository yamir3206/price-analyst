import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/app_config.dart';
import '../models/search_models.dart';
import '../models/wholesale_models.dart';

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => 'ApiException($statusCode): $message';
}

class ApiClient {
  ApiClient({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  Future<SearchSnapshot> search(String query, {bool refresh = false}) async {
    return _postSnapshot('/api/v1/searches', query, refresh: refresh);
  }

  Future<SearchSnapshot> analyze(String query, {bool refresh = false}) async {
    return _postSnapshot('/api/v1/searches/analysis', query, refresh: refresh);
  }

  Future<WholesaleSnapshot> wholesaleSearch(
    String query, {
    bool refresh = false,
  }) async {
    final response = await _client.post(
      AppConfig.apiUri('/api/v1/wholesale/searches'),
      headers: const {'content-type': 'application/json'},
      body: jsonEncode({'query': query, 'refresh': refresh}),
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(
        _readError(response.body),
        statusCode: response.statusCode,
      );
    }

    final decoded = jsonDecode(response.body);
    if (decoded is! Map<String, dynamic>) {
      throw const ApiException('The server returned an invalid response.');
    }
    return WholesaleSnapshot.fromJson(decoded);
  }

  Future<SearchSnapshot> _postSnapshot(
    String path,
    String query, {
    required bool refresh,
  }) async {
    final response = await _client.post(
      AppConfig.apiUri(path),
      headers: const {'content-type': 'application/json'},
      body: jsonEncode({'query': query, 'refresh': refresh}),
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(
        _readError(response.body),
        statusCode: response.statusCode,
      );
    }

    final decoded = jsonDecode(response.body);
    if (decoded is! Map<String, dynamic>) {
      throw const ApiException('The server returned an invalid response.');
    }
    return SearchSnapshot.fromJson(decoded);
  }

  String _readError(String body) {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map<String, dynamic> && decoded['detail'] is String) {
        return decoded['detail'] as String;
      }
    } on FormatException {
      // Fall through to a generic message for non-JSON gateway errors.
    }
    return 'The request could not be completed.';
  }
}
