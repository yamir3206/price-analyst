# Flutter frontend

This directory contains the shared Flutter client for Android, Windows, Web, and later iOS.

Flutter/Dart is not installed in the initial backend environment. After installing Flutter 3.24.x:

```bash
flutter pub get
flutter analyze
flutter test
flutter run -d chrome --dart-define=API_BASE_URL=/api
```

The browser client uses a relative `/api` base so a reverse proxy or development server can route requests. Browser code never calls the user's localhost. Android emulator builds should pass `--dart-define=API_BASE_URL=http://10.0.2.2:8000`; debug Android builds permit cleartext HTTP only for this local-development case. Release builds require HTTPS and keep cleartext traffic disabled.

## Android packaging

The Android runner is checked in under `android/` and is built in the Android GitHub Actions workflow. The reproducible debug package command is:

```bash
flutter pub get
flutter build apk --debug --dart-define=API_BASE_URL=https://api.example.invalid
```

The placeholder URL is only for packaging; configure the real HTTPS backend URL for a device build. The workflow uploads the resulting debug APK as an artifact.

For a signed release, create a private `android/key.properties` from `android/key.properties.example`, point `storeFile` at a private upload keystore, and run:

```bash
flutter build appbundle --release --dart-define=API_BASE_URL=https://api.example.com
```

`key.properties`, keystores, and passwords are ignored and must never be committed. A release build without signing properties is intentionally not configured with the debug key. The Android application ID is currently `com.yamir3206.price_analyst`; change it deliberately before publishing if a different namespace is required.

The application code deliberately keeps API and state logic outside widgets. Search responses drive the local statistics, per-currency price bars, deterministic opportunity views, and the explicit Gemini interpretation flow. Wholesale search uses a separate controller and endpoint so supplier listings never get mixed into retail snapshots.
