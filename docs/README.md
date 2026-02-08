# Install

### Install python modules
```bash
pip install -r requirements.txt
```

### Install nodejs module
```bash
npm i pm2 -g
```

# Usage

### First run
```bash
python application_start.py
```

### Filling in the configuration file
```bash
vim config.json
```

### Second run
```bash
pm2 start application_start.py
```


# Docker

### Build and start
```bash
docker compose up -d --build
```

### Check logs
```bash
docker compose logs -f bot
```

### Stop
```bash
docker compose down
```

# Project structure

- `application_start.py` — lightweight entrypoint for supervisor mode.
- `telegram_bot.py` — lightweight entrypoint for Telegram mode.
- `hosting_bot/common/` — shared config and logging modules.
- `hosting_bot/supervisor/` — internet monitoring + PM2 process control.
- `hosting_bot/telegram/` — bot handlers and shell/file helpers.
