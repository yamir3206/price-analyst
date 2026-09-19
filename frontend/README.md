# Flutter frontend

This directory contains the shared Flutter client for Android, Windows, Web, and later iOS.

Flutter/Dart is not installed in the initial backend environment. After installing Flutter:

```bash
flutter pub get
flutter analyze
flutter test
flutter run -d chrome --dart-define=API_BASE_URL=/api
```

The browser client uses a relative `/api` base so a reverse proxy or development server can route requests. Android emulator builds should pass `API_BASE_URL=http://10.0.2.2:8000`.

Native runner directories can be generated with:

```bash
flutter create . --platforms=android,windows,web
```

The application code deliberately keeps API and state logic outside widgets. Search responses now drive the local statistics, per-currency price bars, and deterministic opportunity views; the Gemini screen remains a Phase 5 placeholder.
