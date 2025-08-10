## Чат-бот учета нерудных материалов (Whisper + GPT + Яндекс Карты)

Функции:
- Приветствие и меню: Добавить, Редактировать, Просмотр
- Ответы текстом или голосом
- Распознавание речи: Whisper (OpenAI)
- Разбор текста: GPT (OpenAI)
- Геокодирование и расстояние: Яндекс Геокодер + Яндекс Маршрутизация (фолбэк OSRM/гаверсин)
- Хранение: только собственная БД (SQLite локально / PostgreSQL на Railway)

### Переменные окружения
- `TELEGRAM_BOT_TOKEN` — токен Telegram-бота
- `OPENAI_API_KEY` — ключ OpenAI (для Whisper и GPT)
- `YANDEX_MAPS_API_KEY` — ключ Яндекс Карт (Геокодер и Маршрутизация)
- `DATABASE_URL` — строка БД. По умолчанию `sqlite:///data.db`. Для Railway/PG: `postgresql+psycopg2://user:pass@host:port/dbname`

### Локальный запуск (Windows PowerShell)
```powershell
pip install -r requirements.txt
$env:TELEGRAM_BOT_TOKEN = "<BOT_TOKEN>"
$env:OPENAI_API_KEY = "<OPENAI_KEY>"
$env:YANDEX_MAPS_API_KEY = "<YANDEX_MAPS_KEY>"
# опционально для PG:
# $env:DATABASE_URL = "postgresql+psycopg2://..."
python -m app.main
```

### Как это работает
- Шаг 1: парсинг сообщения (текст/голос). Извлекаем номер машины, адрес начала/конца (GPT). Геокодируем адреса и считаем расстояние (Яндекс).
- Шаг 2: тип груза, загрузка, выгрузка → вычисляем остаток и сохраняем запись в БД. Просмотр — последние 10, редактирование — через простые ключи (`car=...; from=...; to=...; cargo=...; load=...; unload=...`).

### Деплой на Railway
1. Репозиторий уже содержит `Dockerfile`, `Procfile` (worker), `railway.toml`.
2. Создайте проект на Railway и подключите репозиторий.
3. В разделе Variables задайте:
   - `TELEGRAM_BOT_TOKEN`
   - `OPENAI_API_KEY`
   - `YANDEX_MAPS_API_KEY`
   - `DATABASE_URL` (если используете PostgreSQL плагин Railway, возьмите строку подключения из него)
4. Тип процесса — worker (указан в `Procfile`). Команда запуска: `python -m app.main`.
5. Нажмите Deploy. Логи можно смотреть во вкладке Deployments.

### Замечания
- Whisper принимает голосовые из Telegram (OGG/OPUS) напрямую.
- Яндекс Маршрутизация тарифицируется. Проверьте квоты и лимиты.
- Для продакшен-надёжности БД рекомендуется PostgreSQL.