## Чат-бот учета нерудных материалов (Google stack)

Функции:
- Приветствие и меню: Добавить, Редактировать, Просмотр
- Ответы текстом или голосом (Google Speech-to-Text)
- Разбор текста и извлечение полей (Gemini)
- Геокодирование и расстояние (Google Maps: Geocoding + Directions)
- Хранение заказов в Google Sheets (через сервисный аккаунт)

### Переменные окружения
- `TELEGRAM_BOT_TOKEN` — токен Telegram-бота
- `GSHEET_ID` — ID Google Таблицы (из URL)
- `GSERVICE_ACCOUNT_JSON` — JSON ключ сервисного аккаунта (строка целиком)
- `GOOGLE_MAPS_API_KEY` — ключ Google Maps Platform (Geocoding + Directions)
- `GCP_SERVICE_ACCOUNT_JSON` — JSON сервисного аккаунта для Google Cloud Speech-to-Text (строка целиком)
- `GOOGLE_GENAI_API_KEY` — API key для Gemini (generative-ai)
- `DATABASE_URL` — опционально, по умолчанию `sqlite:///data.db`

### Настройка Google Sheets
1. Создайте проект в Google Cloud Console.
2. Включите Google Sheets API.
3. Создайте сервисный аккаунт и JSON ключ. Содержимое JSON положите в `GSERVICE_ACCOUNT_JSON`.
4. Создайте Google Таблицу, получите её ID из URL.
5. Поделитесь таблицей с email сервисного аккаунта (роль Editor).

### Настройка Google Maps Platform
1. Включите APIs: Geocoding API и Directions API.
2. Создайте ключ и задайте `GOOGLE_MAPS_API_KEY`.

### Настройка Google Speech-to-Text
1. Включите Cloud Speech-to-Text API.
2. Создайте сервисный аккаунт и JSON ключ (может быть тем же, что и для Sheets, если у проекта нужные права).
3. Положите содержимое JSON в `GCP_SERVICE_ACCOUNT_JSON`.

### Настройка Gemini (Generative AI)
1. Получите API key для Gemini и задайте `GOOGLE_GENAI_API_KEY`.

### Локальный запуск
```powershell
pip install -r requirements.txt
$env:TELEGRAM_BOT_TOKEN = "<BOT_TOKEN>"
$env:GSHEET_ID = "<SHEET_ID>"
$env:GSERVICE_ACCOUNT_JSON = "<SERVICE_JSON>"
$env:GOOGLE_MAPS_API_KEY = "<MAPS_KEY>"
$env:GCP_SERVICE_ACCOUNT_JSON = "<SERVICE_JSON>"
$env:GOOGLE_GENAI_API_KEY = "<GEMINI_KEY>"
python -m app.main
```

### Как это работает
- Шаг 1: бот парсит машину/адреса (текст или голос), геокодирует адреса, получает расстояние по маршруту.
- Шаг 2: тип груза, загрузка и выгрузка → считает остаток. Запись сохраняется в БД и синхронизируется в Google Sheets.

### Деплой на Railway
- Заполните Variables значениями выше. Команда запуска — `python -m app.main`.