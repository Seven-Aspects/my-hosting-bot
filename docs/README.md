# Install

### Install python modules
```bash
pip install -r requirements.txt
# includes dbase from GitHub branch codex/analyze-repository-for-improvements
```

### Install nodejs module
```bash
npm i pm2 -g
```

# Usage

### First run
```bash
python main.py supervisor
```

### Filling in the configuration file
```bash
vim config.json
```

### Second run
```bash
pm2 start main.py --interpreter python -- telegram
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

- `main.py` — unified entrypoint (`supervisor` or `telegram` mode).
- `bot/common/` — shared config and logging modules.
- `bot/supervisor/` — internet monitoring + PM2 process control.
- `bot/telegram/` — bot handlers and shell/file helpers.
