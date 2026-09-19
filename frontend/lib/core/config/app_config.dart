import 'package:flutter/foundation.dart';

class AppConfig {
  const AppConfig._();

  static const _configuredBaseUrl = String.fromEnvironment('API_BASE_URL');

  static Uri apiUri(String path) {
    final normalizedPath = path.startsWith('/') ? path : '/$path';

    if (_configuredBaseUrl.isEmpty) {
      // Browser clients use a relative URL so the dev server or reverse proxy
      // owns backend routing. They must never call the user's localhost.
      if (kIsWeb) {
        return Uri.parse(normalizedPath);
      }
      // Override this for an Android emulator with API_BASE_URL=http://10.0.2.2:8000.
      return Uri.parse('http://127.0.0.1:8000$normalizedPath');
    }

    if (_configuredBaseUrl.startsWith('/')) {
      if (normalizedPath.startsWith(_configuredBaseUrl)) {
        return Uri.parse(normalizedPath);
      }
      return Uri.parse('$_configuredBaseUrl$normalizedPath');
    }
    return Uri.parse(_configuredBaseUrl).resolve(normalizedPath);
  }
}
