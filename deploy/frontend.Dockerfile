FROM ghcr.io/cirruslabs/flutter:3.24.0 AS build

WORKDIR /app
COPY frontend/pubspec.yaml ./
RUN flutter pub get
COPY frontend/ ./
RUN flutter build web --release --dart-define=API_BASE_URL=/api

FROM nginx:1.27-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build/web /usr/share/nginx/html

EXPOSE 80
