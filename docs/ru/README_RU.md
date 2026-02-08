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

### Заполнение конфигурационного файла
```bash
vim config.json
```

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
- `bot/common/` — общие модули конфигурации и логирования.
- `bot/supervisor/` — мониторинг интернета + управление PM2-процессами.
- `bot/telegram/` — обработчики Telegram-бота и shell/file-утилиты.
