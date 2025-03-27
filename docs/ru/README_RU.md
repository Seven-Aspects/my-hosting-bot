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
