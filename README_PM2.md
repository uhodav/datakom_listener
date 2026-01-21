[![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/badges/StandWithUkraine.svg)](https://stand-with-ukraine.pp.ua)

#### Ukraine is still suffering from Russian aggression, [please consider supporting Red Cross Ukraine with a donation](https://redcross.org.ua/en/).

[![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner2-direct.svg)](https://stand-with-ukraine.pp.ua)

# Datakom D500 MK3 - PM2 Deployment Guide / Керівництво з розгортання PM2

Production deployment guide for Datakom D500 MK3 telemetry system using PM2 process manager.
Керівництво з production-розгортання телеметричної системи Datakom D500 MK3 з використанням PM2.

## PM2 Installation / Встановлення PM2

PM2 is a process manager for Node.js that works excellent with Python applications.
PM2 - менеджер процесів для Node.js, який чудово працює з Python-застосунками.

### Windows

```powershell
# Install Node.js (if not installed) / Встановити Node.js (якщо не встановлено)
# Download from / Завантажити з https://nodejs.org/

# Install PM2 globally / Встановити PM2 глобально
npm install -g pm2

# For Windows, install pm2-windows-service / Для Windows встановити pm2-windows-service
npm install -g pm2-windows-service

# Install as Windows Service / Встановити як Windows-сервіс
pm2-service-install
```

### Linux/macOS

```bash
# Install Node.js (if not installed) / Встановити Node.js (якщо не встановлено)
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install PM2 globally / Встановити PM2 глобально
npm install -g pm2
```

## Deployment / Розгортання

### 1. Install Python dependencies / Встановити Python-залежності

```bash
pip install -r requirements.txt
```

### 2. Create logs directory / Створити директорію для логів

```bash
mkdir logs
```

### 3. Start services / Запустити сервіси

```bash
# Start all services from ecosystem.config.js / Запустити всі сервіси з ecosystem.config.js
pm2 start ecosystem.config.js

# Or start individually / Або запустити окремо
pm2 start ecosystem.config.js --only datakom-listener
pm2 start ecosystem.config.js --only datakom-api
```

### 4. Configure autostart / Налаштувати автозапуск

```bash
# Save current process list / Зберегти поточний список процесів
pm2 save

# Configure autostart on system boot / Налаштувати автозапуск при старті системи
pm2 startup

# Windows (after pm2-windows-service installation):
# Windows (після встановлення pm2-windows-service):
# Services start automatically on system boot / Сервіси автоматично запускаються при старті системи
```

## Service Management / Управління сервісами

### Basic commands / Основні команди

```bash
# Show process list / Показати список процесів
pm2 list
pm2 ls

# Detailed process information / Детальна інформація про процес
pm2 describe datakom-listener
pm2 describe datakom-api

# Logs (all processes) / Логи (всі процеси)
pm2 logs

# Logs (specific process) / Логи (конкретний процес)
pm2 logs datakom-listener
pm2 logs datakom-api

# Real-time logs / Логи в реальному часі
pm2 logs --lines 50

# Clear logs / Очистити логи
pm2 flush
```

### Restart / Перезапуск

```bash
# Restart all / Перезапустити всі
pm2 restart all

# Restart specific service / Перезапустити конкретний сервіс
pm2 restart datakom-listener
pm2 restart datakom-api

# Reload configuration / Перезавантажити конфігурацію
pm2 reload ecosystem.config.js
```

### Stop / Зупинка

```bash
# Stop all / Зупинити всі
pm2 stop all

# Stop specific service / Зупинити конкретний сервіс
pm2 stop datakom-listener
pm2 stop datakom-api
```

### Remove / Видалення

```bash
# Remove all processes / Видалити всі процеси
pm2 delete all

# Remove specific service / Видалити конкретний сервіс
pm2 delete datakom-listener
pm2 delete datakom-api
```

## Monitoring / Моніторинг

### Real-time monitor / Монітор в реальному часі

```bash
# Terminal monitor / Термінальний монітор
pm2 monit
```

### Web interface (PM2 Plus) / Веб-інтерфейс (PM2 Plus)

```bash
# Register at / Зареєструватися на https://app.pm2.io/
# Get keys and link / Отримати ключі та під'єднати
pm2 link <secret> <public>
```
## Configuration / Конфігурація

File: `ecosystem.config.js` / Файл: `ecosystem.config.js`

Main parameters / Основні параметри:

- **name** - Process name / Назва процесу
- **script** - Path to Python script / Шлях до Python-скрипту
- **interpreter** - 'python' or 'python3' / 'python' або 'python3'
- **instances** - Number of instances (1 for our services) / Кількість інстансів (1 для наших сервісів)
- **autorestart** - Auto-restart on crash / Авторестарт при падінні
- **max_memory_restart** - Restart on memory limit / Рестарт при перевищенні пам'яті
- **env** - Environment variables (DATAKOM_LANG) / Змінні оточення (DATAKOM_LANG)
- **error_file/out_file** - Log file paths / Шляхи до файлів логів
- **restart_delay** - Delay before restart (5 seconds) / Затримка перед рестартом (5 секунд)
- **max_restarts** - Maximum restarts / Максимум рестартів

### Change language / Змінити мову

Edit `ecosystem.config.js` / Редагувати `ecosystem.config.js`:

```javascript
env: {
  DATAKOM_LANG: 'en'  // or 'uk' / або 'uk'
}
```

Then / Потім:

```bash
pm2 reload ecosystem.config.js
```

## Logs / Логи

### Via PM2 / Через PM2

```bash
# Last 200 lines / Останні 200 рядків
pm2 logs --lines 200

# Listener logs / Логи listener
pm2 logs datakom-listener --lines 100

# API logs / Логи API
pm2 logs datakom-api --lines 100
```

### Direct file access / Прямий доступ до файлів

```bash
# Windows
type logs\listener-out.log
type logs\api-out.log

# Linux/macOS
tail -f logs/listener-out.log
tail -f logs/api-out.log
```

## Code Updates / Оновлення коду

```bash
# 1. Stop services / Зупинити сервіси
pm2 stop all

# 2. Update code (git pull, file copy, etc.) / Оновити код (git pull, копіювання файлів тощо)

# 3. Update dependencies / Оновити залежності
pip install -r requirements.txt

# 4. Restart / Перезапустити
pm2 restart all

# Or single command (no downtime) / Або однією командою (без зупинки)
pm2 reload all
```

## Troubleshooting / Усунення проблем

### Processes won't start / Процеси не запускаються

```bash
# Check Python interpreter / Перевірити інтерпретатор Python
python --version

# Windows: if using python.exe, change in ecosystem.config.js
# Windows: якщо використовується python.exe, змінити в ecosystem.config.js
# interpreter: 'python' -> interpreter: 'C:\\Python311\\python.exe'

# Check path / Перевірити шлях
pm2 describe datakom-listener
```

### Constant restarts / Постійні рестарти

```bash
# View error logs / Переглянути логи помилок
pm2 logs datakom-listener --err --lines 50

# Check dependencies / Перевірити залежності
pip list

# Run manually for debugging / Запустити вручну для налагодження
python datakom_listener.py
```

### Logs not writing / Логи не пишуться

```bash
# Ensure logs directory exists / Переконатися що директорія logs існує
mkdir logs

# Restart with log flush / Перезапустити з очищенням логів
pm2 delete all
pm2 flush
pm2 start ecosystem.config.js
```

## Uninstall PM2 / Видалення PM2

```bash
# Windows (if pm2-windows-service installed) / Windows (якщо встановлено pm2-windows-service)
pm2-service-uninstall

# Remove all processes / Видалити всі процеси
pm2 kill

# Uninstall PM2 / Видалити PM2
npm uninstall -g pm2
```

## Quick Start / Швидкий старт

```bash
# 1. Install PM2 / Встановити PM2
npm install -g pm2

# 2. Install Python dependencies / Встановити Python-залежності
pip install -r requirements.txt

# 3. Start services / Запустити сервіси
pm2 start ecosystem.config.js

# 4. Save and configure autostart / Зберегти та налаштувати автозапуск
pm2 save
pm2 startup

# 5. Check status / Перевірити статус
pm2 status

# 6. View logs / Переглянути логи
pm2 logs
```

## Example Output / Приклад виводу

```bash
$ pm2 list
┌─────┬──────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id  │ name             │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├─────┼──────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ 0   │ datakom-listener │ default     │ N/A     │ fork    │ 12345    │ 5m     │ 0    │ online    │ 0.1%     │ 45.2mb   │ user     │ disabled │
│ 1   │ datakom-api      │ default     │ N/A     │ fork    │ 12346    │ 5m     │ 0    │ online    │ 0.2%     │ 67.8mb   │ user     │ disabled │
└─────┴──────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
```

## Useful Links / Корисні посилання

- PM2 Documentation: https://pm2.keymetrics.io/docs/usage/quick-start/
- PM2 for Windows: https://www.npmjs.com/package/pm2-windows-service
- Node.js Downloads: https://nodejs.org/
