# Установка

### Установка Python модуля
```bash
pip install -r requirements.txt
```

### Установка NodeJS модуля
```bash
npm i pm2 -g
```

# Использование

### Первый запуск
```bash
python application_start.py
```

### Заполнение конфигурационного файла
```bash
vim config.json
```

### Второй запуск
```bash
pm2 start application_start.py
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

- `application_start.py` — тонкий entrypoint для режима supervisor.
- `telegram_bot.py` — тонкий entrypoint для Telegram-режима.
- `hosting_bot/common/` — общие модули конфигурации и логирования.
- `hosting_bot/supervisor/` — мониторинг интернета + управление PM2-процессами.
- `hosting_bot/telegram/` — обработчики Telegram-бота и shell/file-утилиты.
