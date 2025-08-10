## Чат-бот учета нерудных материалов

Функции:
- Приветствие и меню: Добавить, Редактировать, Просмотр
- Ответы текстом или голосом
- Распознавание речи: Yandex SpeechKit
- Разбор текста: YandexGPT (фолбэк на простые правила без ключей)
- Расчет расстояния по адресам (Nominatim + OSRM)
- Хранение заказов в БД (SQLite локально / PostgreSQL через Railway)

### Переменные окружения
- `TELEGRAM_BOT_TOKEN` — токен Telegram-бота
- `YANDEX_API_KEY` — API-ключ Yandex Cloud (SpeechKit + Foundation Models)
- `YANDEX_FOLDER_ID` — Folder ID в Yandex Cloud
- `DATABASE_URL` — опционально, например `postgresql+psycopg2://user:pass@host:port/dbname`. По умолчанию `sqlite:///data.db`

### Локальный запуск
1. Python 3.11+
2. Установить зависимости:
   ```bash
   pip install -r requirements.txt
   ```
3. Экспортировать переменные окружения (Windows PowerShell):
   ```powershell
   $env:TELEGRAM_BOT_TOKEN = "<YOUR_TOKEN>"
   $env:YANDEX_API_KEY = "<YOUR_YC_API_KEY>"
   $env:YANDEX_FOLDER_ID = "<YOUR_FOLDER_ID>"
   # опционально
   # $env:DATABASE_URL = "postgresql+psycopg2://..."
   ```
4. Запуск:
   ```bash
   python -m app.main
   ```

### Деплой на Railway
- Репозиторий содержит `Dockerfile` и `Procfile` (тип процесса — worker)
- В Railway создайте проект, подключите репозиторий, в Variables задайте:
  - `TELEGRAM_BOT_TOKEN`
  - `YANDEX_API_KEY`
  - `YANDEX_FOLDER_ID`
  - `DATABASE_URL` (если используете Railway PostgreSQL плагин)
- Стартовая команда: `python -m app.main` (из `Procfile`)

### Примечания
- Если нет ключей Yandex, распознавание голоса будет недоступно, а разбор текста будет по упрощенным правилам.
- Для более точного расчета расстояний можно переключиться на Yandex Maps Routing API (потребуется отдельный ключ).