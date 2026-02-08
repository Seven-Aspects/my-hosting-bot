# Установка

### Установка Python модуля
```bash
pip install -r requirements.txt
# включает dbase из GitHub-ветки codex/analyze-repository-for-improvements
```

### Установка NodeJS модуля
```bash
npm i pm2 -g
```

# Использование

### Первый запуск
```bash
python main.py supervisor
```

### Настройка окружения
```bash
vim .env
```

Основные параметры:
- `BOT_TOKEN`
- `BOT_ADMINS_CHAT_ID` (через запятую)
- `BOT_IGNORE_FOLDERS` (через запятую)
- `BOT_AUTORUN`

Данные рантайма сохраняются в `data/data.json`.

### Второй запуск
```bash
pm2 start main.py --interpreter python -- telegram
```


# Docker

### Сборка и запуск
```bash
docker compose up -d --build
```

### Просмотр логов
```bash
docker compose logs -f bot
```

### Остановка
```bash
docker compose down
```

# Структура проекта

- `main.py` — единый entrypoint (`supervisor` или `telegram`).
- `bot/common/` — общие модули конфигурации, логирования и env-настроек.
- `bot/database/` — слой адаптера БД на базе `dbase`.
- `bot/supervisor/` — мониторинг интернета + управление PM2-процессами.
- `bot/telegram/` — обработчики Telegram-бота и shell/file-утилиты.
