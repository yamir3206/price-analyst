# راهنمای فارسی نصب، اجرا و استقرار Price Analyst

این فایل راهنمای عملی پروژه را از صفر تا اجرای محلی، Docker، سرویس‌های ابری، Colab، هاست اشتراکی و VPS توضیح می‌دهد. مسیرهای داخل دستورها نسبت به ریشهٔ مخزن (`price-analyst/`) هستند.

> **تاریخ بازبینی این راهنما: ۲۰۲۶-۱۰-۰۱.** قیمت، سهمیه و سیاست سرویس‌های شخص ثالث تغییرپذیر است؛ پیش از استقرار نهایی لینک‌های رسمی بخش [سرویس‌های آنلاین و رایگان](#سرویسهای-آنلاین-رایگان-و-محدودیتهای-واقعی) را دوباره بررسی کنید.

## ۱) قبل از نصب: پروژه چه چیزی است؟

Price Analyst یک کلاینت Flutter و یک API مبتنی بر FastAPI است. مسیر داده به شکل زیر است:

```text
Flutter Web/Android/Windows → FastAPI → آداپتورهای مستقل منابع → تحلیل قطعی محلی
                                                       └→ Gemini اختیاری و صریح
```

چند نکتهٔ مهم که از خطاهای عملی جلوگیری می‌کند:

- همهٔ آداپتورهای بازار (`Torob`، `Basalam`، `Digikala` و `Divar`) به‌صورت پیش‌فرض خاموش‌اند. خاموش بودن منبع یعنی برنامه پاسخ صادقانهٔ `no_sources_configured` و فهرست پیشنهادهای خالی می‌دهد؛ دادهٔ ساختگی تولید نمی‌کند.
- تحلیل Gemini اختیاری، سمت سرور و فقط با درخواست صریح endpoint تحلیل است. کلید Gemini را هرگز در Flutter، کد JavaScript یا مخزن قرار ندهید.
- بخش عمدهٔ تحلیل، نرمال‌سازی، آمار، تطبیق و فرصت‌ها محلی و قطعی است و بدون Gemini هم اجرا می‌شود.
- جمع‌آوری عمده‌فروشی مسیر و قرارداد جداگانه دارد (`/api/v1/wholesale/searches`) و فقط با یک فید JSON عمومی HTTPS که خودتان بررسی و مجاز کرده‌اید قابل فعال‌سازی است؛ منبع عمده‌فروشی را با بازار خرده‌فروشی مخلوط نکنید.
- آداپتورها به HTML عمومی تکیه دارند و ممکن است با تغییر سایت، robots.txt، شرایط استفاده یا محدودیت شبکه از کار بیفتند. قبل از فعال‌سازی هر منبع، مجوز، شرایط استفاده، robots و قوانین محل فعالیت خود را بررسی کنید.

## ۲) انتخاب سریع روش اجرا

| هدف | روش پیشنهادی | وضعیت داده و محدودیت |
|---|---|---|
| ساده‌ترین اجرا روی ویندوز بدون Flutter | دوبار کلیک روی `run-windows.bat` (رابط وب فارسی `webui/`) | فقط Python 3.11+ لازم است؛ رابط و API فقط روی همین رایانه |
| فقط آزمایش توسعه‌دهنده | Python virtualenv + backend و Flutter جدا | ساده، ولی باید دو process اجرا شود |
| اجرای کامل با کمترین تنظیم | Docker Compose | API، وب و migration یک‌جا؛ SQLite در volume نام‌دار |
| دموی موقت API | Render یا Railway | خواب/سهمیه/اعتبار و filesystem موقتی را بپذیرید؛ production فرض نکنید |
| وب استاتیک Flutter | Cloudflare Pages یا هر static host | فقط frontend؛ FastAPI را جداگانه میزبانی کنید |
| تمرین و smoke test بدون URL عمومی | Google Colab | runtime موقتی؛ نوت‌بوک in-process، نه سرور دائمی یا tunnel |
| cPanel/هاست اشتراکی | فقط با ASGI واقعی و process manager | بسیاری از هاست‌ها Python 3.11، process دائم یا outbound HTTPS ندارند |
| سرویس پایدار | VPS لینوکس + Docker Compose + Caddy | مسئولیت backup، به‌روزرسانی، فایروال و monitoring با شماست |

## ۳) پیش‌نیازها و دریافت کد

### پیش‌نیازها

- Git
- Python **۳.۱۱ یا جدیدتر** برای backend
- برای Docker: Docker Engine یا Docker Desktop با Compose v2
- برای frontend: Flutter/Dart سازگار با پروژه؛ `frontend/pubspec.yaml` حداقل Flutter `3.22` را می‌خواهد و Dockerfile نسخهٔ `3.24.0` را استفاده می‌کند.
- برای PostgreSQL اختیاری: یک database قابل دسترس با driver موجود در backend

دریافت کد:

```bash
git clone https://github.com/yamir3206/price-analyst.git
cd price-analyst
```

اگر می‌خواهید branch یا commit دیگری را آزمایش کنید:

```bash
git checkout <branch-or-commit>
```

هیچ فایل `.env`، کلید Gemini، password دیتابیس، keystore اندروید یا backup را commit نکنید. `.env` و `backups/` در `.gitignore` هستند.

## ۴) سریع‌ترین اجرای کامل: Docker Compose

### ۴.۱) اجرای محلی

از ریشهٔ مخزن:

```bash
cp .env.example .env
# در صورت نیاز .env را ویرایش کنید؛ مقادیر عمومی و کلیدها را بدون بررسی فعال نکنید.
./deploy/quick-start.sh
```

`quick-start.sh` کارهای زیر را انجام می‌دهد:

1. وجود Docker را بررسی می‌کند؛
2. اگر `.env` وجود نداشته باشد، آن را **فقط یک‌بار** از `.env.example` می‌سازد؛
3. دستور `docker compose -f deploy/docker-compose.yml up --build -d` را اجرا می‌کند؛
4. آدرس وب و دستور readiness را چاپ می‌کند.

اسکریپت `.env` موجود را overwrite نمی‌کند. برنامه پس از آماده شدن روی <http://localhost:8080> است.

```bash
curl --fail http://localhost:8080/api/v1/health
curl --fail http://localhost:8080/api/v1/ready
# صفحهٔ Swagger برای بررسی دستی:
# http://localhost:8080/docs
```

در Compose، سرویس `migrate` ابتدا migrationهای Alembic را تا `head` اجرا می‌کند؛ سپس `api` و بعد `web` آماده می‌شوند. API مستقیماً روی پورت میزبان منتشر نمی‌شود و Nginx مسیر `/api/` را به API داخلی proxy می‌کند؛ بنابراین browser لازم نیست به `localhost` دیگری وصل شود.

### ۴.۲) عملیات روزمره

```bash
docker compose -f deploy/docker-compose.yml ps
docker compose -f deploy/docker-compose.yml logs -f api web
# توقف بدون حذف volume داده
docker compose -f deploy/docker-compose.yml down
# بازسازی پس از تغییر کد یا Dockerfile
docker compose -f deploy/docker-compose.yml up --build -d
# اعتبارسنجی فایل Compose بدون اجرا
docker compose -f deploy/docker-compose.yml config
```

برای حذف volume و دادهٔ SQLite فقط با آگاهی کامل عمل کنید:

```bash
docker compose -f deploy/docker-compose.yml down -v
```

### ۴.۳) SQLite، PostgreSQL و migration در Compose

حالت پیش‌فرض Compose از SQLite در volume نام‌دار `app-data` استفاده می‌کند و `PRICE_ANALYST_DURABLE_CACHE_ENABLED` را برای API فعال می‌کند. این داده cache/snapshot است، اما همچنان باید backup شود. برای PostgreSQL خارجی، قبل از `up` مقدار زیر را در `.env` قرار دهید:

```dotenv
DEPLOY_DATABASE_URL=postgresql+psycopg://price_analyst:REPLACE_ME@db.example.com:5432/price_analyst
```

سپس:

```bash
./deploy/quick-start.sh
```

رمز را URL-encode کنید (مثلاً `@` در password باید به `%40` تبدیل شود)، دسترسی شبکه و TLS دیتابیس را محدود/تنظیم کنید و credential را در secret manager نگه دارید. تغییر SQLite به PostgreSQL انتقال خودکار داده انجام نمی‌دهد؛ برای cache معمولاً می‌توان آن را دوباره ساخت، اما اگر داده‌ای برای شما مهم است قبل از تغییر، برنامهٔ export/backup داشته باشید.

### ۴.۴) backup و HTTPS

Backup سازگار SQLite برای deployment پیش‌فرض:

```bash
./deploy/backup-sqlite.sh
# یا
make deploy-backup
```

خروجی در `backups/` است و نباید فقط روی همان VPS نگه‌داری شود؛ آن را به storage جداگانه کپی و restoration را دوره‌ای امتحان کنید. این script برای PostgreSQL نیست؛ برای PostgreSQL از `pg_dump` و backup رسمی provider استفاده کنید.

برای دامنه‌ای که DNS آن به VPS اشاره می‌کند، Caddy گواهی HTTPS را می‌گیرد و تمدید می‌کند:

```bash
DEPLOY_DOMAIN=prices.example.com \
  docker compose --profile tls -f deploy/docker-compose.yml up --build -d
```

پورت‌های ۸۰ و ۴۴۳ باید از فایروال قابل دسترس باشند. API را مستقیماً روی اینترنت publish نکنید. در production احراز هویت، rate limit و پایش مناسب را هم در gateway یا خود برنامه اضافه کنید؛ این repository baseline امنیتی و headerهای پایه دارد، اما سامانهٔ کامل multi-user با authentication آماده فرض نمی‌شود.

جزئیات تکمیلی Docker در [`deploy/README.md`](deploy/README.md) است.

## ۵) اجرای backend به‌صورت محلی با Python

### ۵.۱) virtualenv و نصب requirements

Linux/macOS و Git Bash:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e 'backend[dev]'
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e 'backend[dev]'
```

این repository فایل `requirements.txt` جداگانه ندارد؛ `backend/pyproject.toml` منبع اصلی dependencyهاست. نصب editable باعث می‌شود import از `backend/src` درست باشد. `backend[dev]` علاوه بر runtime، pytest، ruff و mypy را نصب می‌کند. برای image production، Dockerfile فقط dependencyهای runtime را نصب می‌کند.

### ۵.۲) تنظیم `.env`

```bash
cp .env.example .env
```

برای اجرای عادی محلی، این مقادیر امن‌ترند:

```dotenv
PRICE_ANALYST_ENVIRONMENT=development
PRICE_ANALYST_HOST=0.0.0.0
PRICE_ANALYST_PORT=8000
PRICE_ANALYST_DURABLE_CACHE_ENABLED=false
PRICE_ANALYST_GEMINI_API_KEY=
PRICE_ANALYST_TOROB_ENABLED=false
PRICE_ANALYST_BASALAM_ENABLED=false
PRICE_ANALYST_DIGIKALA_ENABLED=false
PRICE_ANALYST_DIVAR_ENABLED=false
PRICE_ANALYST_WHOLESALE_FEED_ENABLED=false
```

`PRICE_ANALYST_CORS_ORIGINS` یک JSON list است، نه فهرست comma-separated ساده. اگر frontend روی origin دیگری اجرا می‌شود، origin دقیق (scheme و port) را اضافه کنید؛ wildcard را برای deployment عمومی بی‌دلیل استفاده نکنید.

### ۵.۳) migration اختیاری در اجرای مستقیم

وقتی `PRICE_ANALYST_DURABLE_CACHE_ENABLED=false` است، backend از cache حافظه‌ای استفاده می‌کند و برای بالا آمدن آن migration لازم نیست. اگر cache پایدار SQLite/PostgreSQL می‌خواهید:

```bash
# از ریشهٔ مخزن؛ مسیر absolute مانع ساخته‌شدن دو دیتابیس در دو cwd می‌شود.
export PRICE_ANALYST_DATABASE_URL="sqlite:///$PWD/price_analyst.db"
export PRICE_ANALYST_DURABLE_CACHE_ENABLED=true
(cd backend && alembic upgrade head)
```

بررسی migration:

```bash
(cd backend && alembic current)
(cd backend && alembic history)
# فقط با برنامهٔ rollback:
(cd backend && alembic downgrade -1)
```

در PowerShell مقدار `PRICE_ANALYST_DATABASE_URL` را با مسیر absolute مناسب Windows تنظیم کنید و همان دستور Alembic را از `backend/` اجرا کنید. `backend/alembic.ini` و `backend/migrations/` authoritative هستند. Compose این مرحله را خودکار انجام می‌دهد.

### ۵.۴) اجرای API و بررسی سلامت

در shellای که virtualenv فعال و cwd ریشهٔ پروژه است:

```bash
uvicorn price_analyst.main:app \
  --app-dir backend/src \
  --host 0.0.0.0 \
  --port 8000 \
  --reload
```

در shell دیگر:

```bash
curl --fail http://127.0.0.1:8000/api/v1/health
curl --fail http://127.0.0.1:8000/api/v1/ready
curl --fail -X POST http://127.0.0.1:8000/api/v1/searches \
  -H 'content-type: application/json' \
  -d '{"query":"Samsung S24 Ultra 256 GB"}'
```

- `/api/v1/health` زنده بودن process و وضعیت پیکربندی Gemini را گزارش می‌کند.
- `/api/v1/ready` وابستگی‌های local لازم را بررسی می‌کند؛ در cache پایدار، اتصال دیتابیس را هم check می‌کند.
- `POST /api/v1/searches` فقط collection و تحلیل قطعی را انجام می‌دهد.
- `POST /api/v1/searches/analysis` درخواست تفسیر Gemini را صریح می‌کند. بدون کلید، وضعیت `disabled` صحیح است و bug محسوب نمی‌شود.
- Swagger در `/docs` و schema در `/openapi.json` قابل مشاهده است.

## ۶) اجرای frontend Flutter

در ترمینال جداگانه:

```bash
cd frontend
flutter --version
flutter pub get
flutter analyze
flutter test
```

### وب در کنار backend محلی

Flutter web در اجرای جداگانه، به‌صورت پیش‌فرض proxy `/api` ندارد. برای جلوگیری از 404، API را روی ۸۰۰۰ و browser را روی ۳۰۰۰ اجرا کنید؛ `.env.example` همین origin را در CORS پیش‌فرض دارد:

```bash
# ترمینال backend:
uvicorn price_analyst.main:app --app-dir backend/src --host 0.0.0.0 --port 8000

# ترمینال frontend:
cd frontend
flutter run -d chrome --web-port 3000 \
  --dart-define=API_BASE_URL=http://localhost:8000
```

اگر پورت/دامنهٔ frontend فرق دارد، همان origin را در `PRICE_ANALYST_CORS_ORIGINS` اضافه و backend را restart کنید. در deployment هم‌origin (Compose یا static host با API proxy) از `--dart-define=API_BASE_URL=/api` استفاده می‌شود.

برای Android emulator:

```bash
flutter run -d <android-device> \
  --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

`10.0.2.2` فقط مسیر emulator Android به host است؛ برای دستگاه فیزیکی باید IP قابل دسترس host یا HTTPS بدهید. HTTP cleartext برای debug محلی است؛ release باید HTTPS داشته باشد.

ساخت web برای انتشار:

```bash
flutter build web --release --dart-define=API_BASE_URL=https://api.example.com
```

ساخت خروجی Android debug و release در [`frontend/README.md`](frontend/README.md) توضیح داده شده است. signing key را وارد مخزن نکنید.

## ۶-الف) رابط وب فارسی سبک (بدون Flutter، Node یا Docker)

اگر نمی‌خواهید Flutter نصب کنید، پوشهٔ [`webui/`](webui/README.md) یک رابط کاربری فارسی و راست‌به‌چپ دارد که فقط با HTML/CSS/JavaScript ساده و یک اسکریپت Python (فقط کتابخانهٔ استاندارد) اجرا می‌شود.

**ویندوز — یک کلیک:**

1. Python نسخهٔ ۳٫۱۱ یا بالاتر را از <https://www.python.org/downloads/> نصب کنید و گزینهٔ **Add python.exe to PATH** را تیک بزنید.
2. روی فایل **`run-windows.bat`** در ریشهٔ مخزن دوبار کلیک کنید.

در اجرای اول، `.venv` ساخته می‌شود، backend با `pip` نصب می‌شود و `.env` از روی `.env.example` ساخته می‌شود؛ سپس backend اجرا و مرورگر روی `http://127.0.0.1:8080` باز می‌شود. اجراهای بعدی بلافاصله شروع می‌شوند. برای نصب دوباره، پوشهٔ `.venv` را حذف کنید.

**اجرای دستی (هر سیستم‌عامل):**

```bash
python -m venv .venv
.venv\Scripts\activate        # لینوکس/مک: . .venv/bin/activate
python -m pip install -e backend
python webui/serve.py --start-backend --open
```

اگر backend از قبل اجرا شده، فقط رابط را اجرا کنید: `python webui/serve.py --backend http://127.0.0.1:8000`

اگر خطای `WinError 10013` یا «پورت در حال استفاده» دیدید: ویندوز برخی بازه‌های پورت را برای Hyper-V، WSL یا Docker رزرو می‌کند، یا برنامهٔ دیگری از آن پورت استفاده می‌کند. اجراکننده پیش از استفاده، پورت‌های ۸۰۰۰ (backend) و ۸۰۸۰ (رابط) را بررسی می‌کند و در صورت نیاز خودکار سراغ یک پورت آزاد می‌رود و نشانی جدید را چاپ می‌کند؛ مرورگر هم روی همان نشانی باز می‌شود. برای انتخاب دستی: `run-windows.bat --port 8090 --backend-port 8010`. برای دیدن بازه‌های رزروشده: `netsh interface ipv4 show excludedportrange protocol=tcp`

این رابط شامل جستجوی خرده‌فروشی، وضعیت منابع، آمار و نمودار جداگانه برای هر واحد پول، فرصت‌ها، تحلیل اختیاری Gemini و جستجوی عمده‌فروشی جداگانه است. مرورگر فقط به آدرس‌های نسبی `/api/v1/...` درخواست می‌دهد و `serve.py` آن‌ها را به backend منتقل می‌کند؛ بنابراین تنظیم CORS لازم نیست. رابط به‌صورت پیش‌فرض فقط روی `127.0.0.1` در دسترس است، چون API احراز هویت ندارد.

## ۷) تنظیمات کامل و معنای متغیرها

منبع authoritative همهٔ نام‌ها و defaultها فایل [`.env.example`](.env.example) است. جدول زیر گروه‌بندی عملی آن‌هاست؛ نام متغیرها را تغییر ندهید.

### پایه

| متغیر | کاربرد |
|---|---|
| `PRICE_ANALYST_ENVIRONMENT` | یکی از `development`، `test`، `staging`، `production` |
| `PRICE_ANALYST_HOST` / `PRICE_ANALYST_PORT` | bind backend؛ providerهای cloud معمولاً port را با `$PORT` به command می‌دهند |
| `PRICE_ANALYST_DATABASE_URL` | SQLite یا `postgresql+psycopg://...` |
| `PRICE_ANALYST_CORS_ORIGINS` | JSON list از originهای مجاز؛ برای frontend جداگانه دقیق تنظیم شود |

### Gemini

`PRICE_ANALYST_GEMINI_API_KEY`، `PRICE_ANALYST_GEMINI_MODEL`، `PRICE_ANALYST_MAX_GEMINI_INPUT_TOKENS`، `PRICE_ANALYST_MAX_GEMINI_OUTPUT_TOKENS`، `PRICE_ANALYST_MAX_OFFERS_TO_ANALYZE`، `PRICE_ANALYST_GEMINI_TIMEOUT_SECONDS`، `PRICE_ANALYST_GEMINI_CACHE_TTL_SECONDS`، `PRICE_ANALYST_GEMINI_CACHE_MAX_ENTRIES`، `PRICE_ANALYST_GEMINI_CONCURRENCY`، `PRICE_ANALYST_GEMINI_MIN_INTERVAL_SECONDS` و `PRICE_ANALYST_ANALYSIS_VERSION` سقف ورودی/خروجی، timeout، cache، همزمانی و نسخهٔ prompt را کنترل می‌کنند. کلید فقط server-side است. خالی گذاشتن کلید، Gemini را graceful غیرفعال می‌کند.

### collection، retry و cache

- `PRICE_ANALYST_SOURCE_TIMEOUT_SECONDS`: timeout هر منبع.
- `PRICE_ANALYST_MAX_SEARCH_CANDIDATES` و `PRICE_ANALYST_MAX_DETAIL_CANDIDATES`: سقف candidateها و detail fetch.
- `PRICE_ANALYST_SOURCE_CONCURRENCY` و `PRICE_ANALYST_SOURCE_MIN_INTERVAL_SECONDS`: همزمانی محدود و فاصلهٔ درخواست‌ها.
- `PRICE_ANALYST_SOURCE_FAILURE_THRESHOLD` و `PRICE_ANALYST_SOURCE_COOLDOWN_SECONDS`: circuit breaker موقت.
- `PRICE_ANALYST_RETRY_MAX_ATTEMPTS`، `PRICE_ANALYST_RETRY_BASE_DELAY_SECONDS` و `PRICE_ANALYST_RETRY_MAX_DELAY_SECONDS`: retry/backoff محدود.
- `PRICE_ANALYST_SNAPSHOT_CACHE_TTL_SECONDS`، `PRICE_ANALYST_DURABLE_CACHE_ENABLED` و `PRICE_ANALYST_DURABLE_CACHE_MAX_ENTRIES`: عمر و محل cache؛ durable را فقط بعد از migration فعال کنید.
- `PRICE_ANALYST_ANALYSIS_MATCH_THRESHOLD` و `PRICE_ANALYST_ANALYSIS_MAX_OPPORTUNITIES`: آستانهٔ تطبیق و سقف فرصت‌های محلی.

### منابع خرده‌فروشی

`PRICE_ANALYST_TOROB_ENABLED`/`PRICE_ANALYST_TOROB_BASE_URL`، `PRICE_ANALYST_BASALAM_ENABLED`/`PRICE_ANALYST_BASALAM_BASE_URL`، `PRICE_ANALYST_DIGIKALA_ENABLED`/`PRICE_ANALYST_DIGIKALA_BASE_URL` و `PRICE_ANALYST_DIVAR_ENABLED`/`PRICE_ANALYST_DIVAR_BASE_URL` به‌همراه `PRICE_ANALYST_DIVAR_CITY` و `PRICE_ANALYST_DIVAR_CATEGORY` هر منبع را مستقل کنترل می‌کنند. هیچ‌کدام را صرفاً برای «تست سریع» روی production روشن نکنید؛ fixture و mocked HTTP در تست‌ها آفلاین‌اند.

### عمده‌فروشی

`PRICE_ANALYST_WHOLESALE_FEED_ENABLED`، `PRICE_ANALYST_WHOLESALE_FEED_URL`، `PRICE_ANALYST_WHOLESALE_FEED_SOURCE`، `PRICE_ANALYST_WHOLESALE_RESPONSE_MAX_BYTES`، `PRICE_ANALYST_MAX_WHOLESALE_LISTINGS`، `PRICE_ANALYST_WHOLESALE_CONCURRENCY`، `PRICE_ANALYST_WHOLESALE_MIN_INTERVAL_SECONDS` و `PRICE_ANALYST_WHOLESALE_TIMEOUT_SECONDS` فقط برای فید عمومی JSON بررسی‌شده هستند. URL باید HTTPS عمومی و مجاز باشد؛ endpoint یا منبع مبهم/خصوصی را جایگزین نکنید.

### متغیرهای Compose

- `DEPLOY_DATABASE_URL`: override دیتابیس برای `migrate` و `api` در Compose.
- `DEPLOY_DOMAIN`: دامنهٔ Caddy در profile `tls`.
- `DEPLOY_WEB_PORT`: پورت میزبان web در حالت پیش‌فرض؛ default `8080`.

## ۸) تست کامل و چرخهٔ عیب‌یابی

### تست‌های backend

```bash
# از ریشه و با virtualenv فعال
pytest backend/tests
ruff check backend/src backend/tests
mypy backend/src
```

یا:

```bash
make backend-test
make backend-lint
```

تست‌ها به سایت‌های زنده وابسته نیستند؛ fixtureهای HTML و HTTP mock دارند. قبل از فعال‌سازی منبع واقعی، ابتدا parser/adapter همان منبع را با fixture بررسی کنید.

### تست frontend

```bash
make frontend-analyze
make frontend-test
```

نیازمند نصب Flutter است. CI فایل‌های workflow موجود را هم اجرا می‌کند.

### smoke test دستی

```bash
curl --fail http://localhost:8080/api/v1/ready
curl --fail http://localhost:8080/
# انتظار می‌رود صفحهٔ HTML وب و JSON وضعیت ready دریافت شود.
```

در صورت خاموش بودن همهٔ منابع، smoke test موفق است اگر پاسخ search وضعیت `no_sources_configured`، پیشنهادهای خالی و statusهای منابع را صادقانه نشان دهد؛ این به معنای جمع‌آوری موفق از بازارها نیست.

## ۹) خطاهای رایج و راه‌حل

### `docker: command not found` یا Compose در دسترس نیست

Docker Engine/Desktop و Compose v2 را نصب کنید و با `docker version` و `docker compose version` بررسی کنید. اگر Docker در محیط شما ممنوع است، بخش Python محلی را اجرا کنید؛ `quick-start.sh` بدون Docker عمداً متوقف می‌شود.

### API با `ModuleNotFoundError: price_analyst` بالا نمی‌آید

virtualenv را فعال کنید و `python -m pip install -e 'backend[dev]'` را از ریشهٔ مخزن اجرا کنید؛ یا حتماً `uvicorn` را با `--app-dir backend/src` اجرا کنید.

### Alembic می‌گوید `No config file` یا migration پیدا نشد

دستور را از ریشه با `(cd backend && alembic upgrade head)` اجرا کنید. `backend/alembic.ini`، `backend/migrations/` و `PYTHONPATH` باید در دسترس باشند. برای مسیر SQLite، URL absolute بدهید تا migration و API به دو فایل متفاوت وصل نشوند.

### `/ready` کد ۵۰۳ می‌دهد

در حالت durable، URL دیتابیس، DNS، credential، firewall و migration را بررسی کنید:

```bash
docker compose -f deploy/docker-compose.yml logs migrate api
(cd backend && alembic current)
```

`/ready` به در دسترس بودن سایت‌های marketplace یا Gemini نیاز ندارد؛ خرابی آن‌ها نباید readiness دیتابیس را پنهان کند.

### frontend خطای CORS یا 404 برای `/api` دارد

برای Flutter web جدا از backend، `API_BASE_URL=http://localhost:8000` و origin frontend مثل `http://localhost:3000` را تنظیم کنید. برای Compose/static reverse proxy از `/api` استفاده کنید، نه URL اشتباه backend. در browser، `localhost` یعنی کامپیوتر کاربر؛ URL خصوصی یا `127.0.0.1` را در build عمومی قرار ندهید.

### frontend روی Android به `Connection refused` می‌رسد

`127.0.0.1` روی emulator خود دستگاه است. از `10.0.2.2:8000` برای Android emulator، IP شبکه برای دستگاه فیزیکی، و HTTPS برای release استفاده کنید. پورت backend باید روی `0.0.0.0` bind و در firewall قابل دسترس باشد.

### جست‌وجو فهرست خالی می‌دهد

`*_ENABLED`ها عمداً default=false هستند. `GET /health` و response `source_statuses` را بخوانید. فعال‌سازی هر منبع بدون بررسی شرایط استفاده، robots و دسترسی مجاز توصیه نمی‌شود. تغییر HTML سایت هم می‌تواند parser را stale کند.

### Gemini کار نمی‌کند

خالی بودن `PRICE_ANALYST_GEMINI_API_KEY` یعنی feature خاموش است. اگر کلید دارید، آن را فقط در محیط backend secret تنظیم کنید، نام model، quota، timeout و log را بررسی کنید و از endpoint `/api/v1/searches/analysis` استفاده کنید؛ endpoint عادی عمداً Gemini را فراخوانی نمی‌کند.

### `git` یا Python dependency در شبکهٔ سازمانی نصب نمی‌شود

proxy/CA سازمان، دسترسی PyPI/Git و certificate را در همان محیط تنظیم کنید. timeout را بی‌دلیل زیاد نکنید. هیچ secret را برای رفع این خطا در issue، notebook یا log چاپ نکنید.

## ۱۰) استقرار روی سرویس‌های آنلاین و رایگان

این گزینه‌ها برای demo/prototype هستند، نه وعدهٔ «رایگان و دائمی». محدودیت‌ها بر اساس اسناد رسمی در تاریخ ابتدای این راهنما بررسی شده‌اند و ممکن است تغییر کنند.

### ۱۰.۱) Render: مناسب برای API آزمایشی، نه SQLite پایدار

برای یک Web Service پایتونی:

- Repository: همین Git repository
- Build command: `python -m pip install -e backend`
- Start command: `uvicorn price_analyst.main:app --app-dir backend/src --host 0.0.0.0 --port $PORT`
- Health check path: `/api/v1/ready`
- متغیرهای environment: `PRICE_ANALYST_ENVIRONMENT=production`، `PRICE_ANALYST_DURABLE_CACHE_ENABLED=false`، تمام source flagها `false`، و در صورت نیاز secret `PRICE_ANALYST_GEMINI_API_KEY`.

در dashboard نام commandها ممکن است تغییر کند؛ اصل مهم این است که process روی `$PORT` ارائه‌شدهٔ Render گوش دهد. برای frontend، web Flutter را جداگانه روی static host بسازید و `PRICE_ANALYST_CORS_ORIGINS` را با origin نهایی آن تنظیم کنید؛ مثلاً `PRICE_ANALYST_CORS_ORIGINS=["https://app.example.com"]` (مقدار باید JSON معتبر باشد).

طبق [مستندات رسمی Render دربارهٔ Free](https://render.com/docs/free)، سرویس رایگان پس از ۱۵ دقیقه idle می‌خوابد و cold start دارد، filesystem آن ephemeral است و SQLite محلی با restart/redeploy قابل اتکا نیست؛ سهمیهٔ Web Service رایگان حدود ۷۵۰ ساعت instance در ماه است و Free Postgres پس از ۳۰ روز منقضی می‌شود. Render خود این tier را برای production توصیه نمی‌کند. بنابراین این روش را برای demo موقت یا API بدون state پایدار به‌کار ببرید، نه production و نه backup.

### ۱۰.۲) Railway: trial/credit، نه free forever نامحدود

یک service از repository بسازید و build/install و start command معادل زیر را تنظیم کنید:

```bash
python -m pip install -e backend
uvicorn price_analyst.main:app --app-dir backend/src --host 0.0.0.0 --port $PORT
```

اگر cache پایدار لازم است، PostgreSQL جدا و migration را در release/deploy command اجرا کنید؛ SQLite روی filesystem سرویس را durable فرض نکنید. مقدار `PRICE_ANALYST_DATABASE_URL` و `PRICE_ANALYST_DURABLE_CACHE_ENABLED=true` را به صورت secret variable بدهید و پیش از start:

```bash
cd backend && alembic upgrade head
```

طبق [صفحهٔ رسمی Railway دربارهٔ Free Trial](https://docs.railway.com/pricing/free-trial)، trial جدید یک اعتبار یک‌بارهٔ **۵ دلار برای حداکثر ۳۰ روز** دارد و بعد از آن Free plan فقط **۱ دلار credit ماهانه** می‌دهد؛ هزینهٔ مصرف، پایان trial و وضعیت volume/stateful storage را پیش از deploy بررسی کنید. Railway را به‌عنوان «رایگان نامحدود برای همیشه» معرفی نکنید. برای frontend می‌توانید خروجی web را جداگانه روی Pages بگذارید.

### ۱۰.۳) Cloudflare Pages: فقط Flutter Web استاتیک

Cloudflare Pages برای فایل‌های build شده مناسب است؛ FastAPI و process طولانی را به Pages نسبت ندهید.

```bash
cd frontend
flutter pub get
flutter build web --release --dart-define=API_BASE_URL=https://YOUR-API.example.com
```

محتویات `frontend/build/web` را با روش upload/direct deployment یا pipeline مورد اعتماد خود در Pages منتشر کنید. اگر Git integration برای نصب Flutter را استفاده می‌کنید، نسخهٔ Flutter را pin کنید؛ Flutter در compile time مقدار `API_BASE_URL` را داخل خروجی قرار می‌دهد و تغییر variable بعد از build به‌تنهایی URL را عوض نمی‌کند. سپس origin دامنهٔ Pages را در `PRICE_ANALYST_CORS_ORIGINS` backend قرار دهید.

[محدودیت‌های رسمی Cloudflare Pages](https://developers.cloudflare.com/pages/platform/limits/) شامل سقف‌هایی مانند ۵۰۰ build در ماه، ۲۰٬۰۰۰ فایل در هر سایت و ۲۵ MiB برای هر فایل در پلن رایگان است؛ Pages Functions هم سهمیهٔ مربوط به Workers دارد. این محدودیت‌ها جای database یا API دائمی را نمی‌گیرند.

### ۱۰.۴) Hugging Face و static hostingهای دیگر

Hugging Face [Static Spaces](https://huggingface.co/docs/hub/spaces-overview) می‌تواند برای خروجی استاتیک Flutter مناسب باشد، اما Gradio/Docker Space را بدون بررسی plan و هزینه، backend رایگان FastAPI فرض نکنید. هر static host دیگری (GitHub Pages، Netlify و مشابه) فقط frontend را میزبانی می‌کند؛ API باید جدا و با HTTPS و CORS صحیح در دسترس باشد. قبل از انتخاب، این موارد را check کنید: build command، حجم artifact، SPA fallback به `index.html`، HTTPS، custom domain و محدودیت outbound/API.

## ۱۱) Google Colab: فقط notebook و smoke test در همان runtime

Colab برای اجرای تعاملی و موقتی خوب است، نه میزبانی عمومی دائمی. [FAQ رسمی Google Colab](https://research.google.com/colaboratory/faq.html) منابع رایگان را تضمین‌شده/نامحدود نمی‌داند و دربارهٔ file hosting، media serving، public web service و دور زدن رابط notebook در managed runtime محدودیت دارد. به همین دلیل این راهنما راهکار ngrok/tunnel یا FastAPI public server روی Colab ارائه نمی‌کند.

فایل آماده در [`notebooks/price_analyst_colab.ipynb`](notebooks/price_analyst_colab.ipynb) است و این مراحل را انجام می‌دهد:

1. clone repository؛
2. نصب `backend[dev]`؛
3. تنظیم SQLite موقت، Gemini خاموش و تمام sourceها خاموش؛
4. import کردن app؛
5. اجرای `TestClient` برای `/health`، `/ready` و search آفلاین؛
6. اجرای اختیاری `pytest backend/tests`.

روش استفاده:

1. فایل را در Colab باز و سلول‌ها را به ترتیب اجرا کنید.
2. به repository عمومی و branch پیش‌فرض دسترسی داشته باشید. برای ref دیگر، قبل از سلول clone مقدار `PRICE_ANALYST_REF` را تغییر دهید.
3. انتظار نداشته باشید runtime، فایل SQLite یا process را بعد از قطع session نگه دارد.
4. برای URL عمومی واقعی از Compose روی VPS یا یک سرویس web استفاده کنید.

## ۱۲) هاست اشتراکی و cPanel

هاست اشتراکی فقط زمانی گزینهٔ واقعی است که provider صریحاً این موارد را پشتیبانی کند:

- Python 3.11+ و ساخت virtualenv؛
- اجرای ASGI با Uvicorn/Gunicorn یا Passenger و process manager پایدار؛
- تنظیم environment variable/secret بدون قرار دادن آن در public web root؛
- reverse proxy برای HTTPS و route؛
- process timeout و memory کافی؛
- outbound HTTPS مجاز برای منابعی که مجاز به استفاده از آن‌ها هستید؛
- PostgreSQL خارجی/پایدار در صورت نیاز.

بسیاری از هاست‌های cPanel فقط PHP یا WSGI محدود ارائه می‌دهند، process طولانی را kill می‌کنند یا اجازهٔ Docker/worker/outbound را نمی‌دهند. در چنین حالتی FastAPI را آنجا نصب نکنید؛ frontend Flutter را به‌صورت static upload کنید و API را روی VPS/سرویس ASGI جدا اجرا کنید.

اگر provider ASGI دارد، الگوی کلی (نه command قطعی همهٔ hostها) این است:

```bash
python3.11 -m venv ~/virtualenvs/price-analyst
source ~/virtualenvs/price-analyst/bin/activate
python -m pip install -e /path/to/price-analyst/backend
# فرمان واقعی start را طبق panel/provider تنظیم کنید:
uvicorn price_analyst.main:app --app-dir /path/to/price-analyst/backend/src --host 0.0.0.0 --port "$PORT"
```

پورت و socket را provider تعیین می‌کند. اگر shared host فقط یک database MySQL دارد، آن را با این پروژه بدون بررسی SQLAlchemy driver و migration معادل نگیرید؛ PostgreSQL یا SQLite پایدار مورد نیاز را فراهم کنید. کلید Gemini و credential را در panel secret بگذارید.

## ۱۳) VPS پیشنهادی برای استقرار پایدار

برای Ubuntu/Debian جدید:

```bash
ssh deploy@YOUR_SERVER
sudo apt update
sudo apt install -y git ufw
# Docker را طبق مستندات رسمی Docker برای توزیع خود نصب کنید.
git clone https://github.com/yamir3206/price-analyst.git
cd price-analyst
cp .env.example .env
```

فایروال حداقلی:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

`.env` را با editor امن تنظیم کنید: `DEPLOY_DOMAIN`، secretها، CORS و در صورت نیاز PostgreSQL. سپس:

```bash
DEPLOY_DOMAIN=prices.example.com \
  docker compose --profile tls -f deploy/docker-compose.yml up --build -d
docker compose -f deploy/docker-compose.yml ps
curl --fail https://prices.example.com/api/v1/ready
```

در زمان update:

```bash
git pull --ff-only
DEPLOY_DOMAIN=prices.example.com \
  docker compose --profile tls -f deploy/docker-compose.yml up --build -d
```

قبل از update از SQLite backup بگیرید یا برای PostgreSQL از `pg_dump` استفاده کنید. log rotation، monitoring، unattended security updates، محدودیت SSH، backup خارج از VPS و برنامهٔ بازگردانی را خودتان اضافه کنید. پورت ۸۰۰۰ داخلی است؛ پورت ۸۰۸۰ را هم اگر از Caddy استفاده می‌کنید عمومی نکنید و با firewall/security group محدود کنید.

## ۱۴) منطق health، امنیت و محدودیت‌های عملیاتی

- `/health` برای liveness و `/ready` برای readiness است؛ health بازارها یا Gemini را تضمین نمی‌کند.
- responseها request ID و headerهای امنیتی پایه دارند، اما اگر API عمومی و چندکاربره است authentication/authorization و rate limiting لازم است.
- کل dataset کامل محلی نگه‌داری می‌شود؛ projection ارسالی به Gemini محدود است و raw HTML/URL ارسال نمی‌شود.
- retry، timeout، concurrency، pacing، circuit breaker و cache bounded هستند؛ افزایش سقف‌ها بدون ظرفیت و policy منبع، فشار و هزینه را زیاد می‌کند.
- SQLite برای یک single-host کوچک قابل استفاده است، اما برای چند replica یا production جدی PostgreSQL و backup/monitoring مناسب‌تر است.
- دادهٔ market ممکن است stale یا ناقص باشد؛ `partial` و source statusها را در UI/API بخوانید و قیمت‌ها را به‌عنوان تضمین تجاری تلقی نکنید.

## ۱۵) چک‌لیست نهایی قبل از تحویل

- [ ] `.env` از repository خارج است و secretها در log/Flutter نیستند.
- [ ] `pytest backend/tests`، `ruff` و `mypy` موفق شده‌اند.
- [ ] `flutter analyze` و `flutter test` در صورت نصب Flutter موفق شده‌اند.
- [ ] `docker compose ... config` موفق است و migration تا `head` اجرا شده است.
- [ ] `/api/v1/health` و `/api/v1/ready` با curl پاسخ درست می‌دهند.
- [ ] backup و restoration آزمایشی انجام شده و backup روی همان disk تنها نسخه نیست.
- [ ] CORS فقط originهای لازم را دارد و API مستقیم بدون gateway/auth عمومی نشده است.
- [ ] sourceهای واقعی فقط بعد از review حقوقی/فنی و با rate limit مناسب فعال شده‌اند.
- [ ] برای cloud رایگان، sleep، quota، ephemeral filesystem، credit و پایان trial به کارفرما/کاربر اعلام شده است.

## اسناد مرجع برای توسعهٔ آینده و Agent

برای اینکه توسعه‌های بعدی با قراردادهای فعلی هماهنگ بمانند، Agent باید ابتدا [`AGENTS.md`](AGENTS.md) را بخواند و سپس این اسناد را بررسی کند:

- [`docs/engineering-contract.md`](docs/engineering-contract.md): قوانین معماری، داده، امنیت، performance و backward compatibility
- [`docs/api-contract.md`](docs/api-contract.md): قرارداد HTTP نسخهٔ v1 و semantics endpointها
- [`docs/openapi.json`](docs/openapi.json): snapshot ماشین‌خوان OpenAPI؛ پس از تغییر API با `python backend/scripts/export_openapi.py` بازتولید شود
- [`docs/extension-guide.md`](docs/extension-guide.md): روش افزودن source، endpoint، migration، AI و Flutter بدون شکستن قابلیت‌ها
- [`docs/roadmap.md`](docs/roadmap.md): milestoneهای آینده و non-goalها
- [`docs/agent-task-template.md`](docs/agent-task-template.md): قالب تحلیل، برنامه‌ریزی، تست و گزارش هر تغییر

## لینک‌های داخلی

- [راهنمای انگلیسی پروژه](README.md)
- [راهنمای deployment](deploy/README.md)
- [راهنمای backend](backend/README.md)
- [راهنمای Flutter](frontend/README.md)
- [سیاست جمع‌آوری](docs/scraping-policy.md)
- [امنیت](docs/security.md) و [مدل تهدید](docs/threat-model.md)
- [نوت‌بوک Colab](notebooks/price_analyst_colab.ipynb)
