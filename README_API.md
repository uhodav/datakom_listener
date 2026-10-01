[![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/badges/StandWithUkraine.svg)](https://stand-with-ukraine.pp.ua)

#### Ukraine is still suffering from Russian aggression, [please consider supporting Red Cross Ukraine with a donation](https://redcross.org.ua/en/).

[![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner2-direct.svg)](https://stand-with-ukraine.pp.ua)

# Datakom D500 MK3 API Server

REST API сервер для доступа к телеметрии контроллера Datakom D500 MK3.

## Архитектура

Система состоит из двух компонентов:

1. **datakom_listener.py** - Слушатель TCP порта (настраивается в config.py), принимает данные от контроллера
2. **api_server.py** - REST API сервер (настраивается в config.py), предоставляет HTTP доступ к данным

## Конфигурация

Все настройки портов и языка в файле **config.py**:

```python
# TCP Listener configuration
LISTENER_HOST = "0.0.0.0"
LISTENER_PORT = 8760

# API Server configuration
API_HOST = "0.0.0.0"
API_PORT = 8765

# Language settings
DEFAULT_LANGUAGE = "uk"  # uk, en, ru
```

## Установка

### 1. Установить зависимости

```bash
pip install -r requirements.txt
```

### 2. Запустить сервисы

#### Рекомендуется: PM2 (автоперезапуск, логи, мониторинг)

```bash
# Установить PM2
npm install -g pm2

# Запустить оба сервиса
pm2 start ecosystem.config.js

# Сохранить и настроить автозапуск
pm2 save
pm2 startup

# Управление
pm2 logs                    # Просмотр логов
pm2 status                  # Статус сервисов
pm2 restart all             # Перезапуск
pm2 stop all                # Остановка
```

📖 Detailed documentation / Детальна документація: [README_PM2.md](README_PM2.md)

## API Endpoints

### Web Interface / Веб-інтерфейс
- **https://your-domain.com/api/health** - API Health Check / Перевірка стану API
- **https://your-domain.com/api_test.html** - Interactive API Tester / Інтерактивний тестер API
- **http://localhost:8765/docs** - Swagger UI Documentation (local only) / Swagger документація (тільки локально)

### GET /api/health
Server and connection health check / Перевірка стану сервера та підключення

**Response / Відповідь:**
```json
{
  "status": "ok",
  "time": "2026-01-21T07:39:15.773Z",
  "connect_state": "Connected",
  "date_time_change_state": "2026-01-21T05:57:42.193Z",
  "listener_running": true,
  "last_error": null
}
```

### GET /api/dump_devm?id=ID1,ID2,...&language=LANG
Get parameters (all or by ID) / Отримати параметри (всі або по ID)

**Parameters / Параметри:**
- `id` (optional) - Comma-separated ID list / Список ID через кому
- `language` (optional) - Language code: `uk`, `en`, `ru` (adds translations to `title` field) / Код мови: `uk`, `en`, `ru` (додає переклади в поле `title`)

**Examples / Приклади:**
```bash
# Production / Продакшн
curl https://your-domain.com/api/dump_devm

# Specific parameters / Конкретні параметри
curl https://your-domain.com/api/dump_devm?id=0,5,10

# With Ukrainian translations / З українськими перекладами
curl https://your-domain.com/api/dump_devm?language=uk

# Specific parameters with translations / Конкретні параметри з перекладами
curl "https://your-domain.com/api/dump_devm?id=19,237,239&language=uk"

# Local access / Локальний доступ
curl http://localhost:8765/api/dump_devm?language=uk
```

**Response / Відповідь:**
```json
{
  "success": true,
  "result": [
    {
      "id": 19,
      "label": "Information ModBus Port",
      "title": "ModBus порт",
      "value": 502,
      "unit": ""
    },
    {
      "id": 237,
      "label": "Engine RPM",
      "title": "Обороти двигуна",
      "value": 1497,
      "unit": "RPM"
    },
    {
      "id": 239,
      "label": "Engine Battery Voltage1",
      "title": "Напруга акумулятора 1",
      "value": 14.57,
      "unit": "Vdc"
    }
  ],
  "cached": true,
  "timestamp": "2026-01-21T10:30:00.000Z"
}
```

**Note / Примітка:** The `title` field contains the translated parameter name if `language` parameter is specified. Without language, `title` will be empty string. / Поле `title` містить перекладену назву параметра, якщо вказано параметр `language`. Без мови `title` буде порожнім рядком.

**Supported languages / Підтримувані мови:**
- `uk` - Українська (default / за замовчуванням)
- `en` - English
- `ru` - Москальска

**Translation examples / Приклади перекладів:**
```bash
# English
curl "https://your-domain.com/api/dump_devm?id=237&language=en"
# title: "Engine RPM"

# Ukrainian / Українська
curl "https://your-domain.com/api/dump_devm?id=237&language=uk"
# title: "Обороти двигуна"
```
```

### GET /api/dump_devm_param_names?language=LANG
Get list of all parameter IDs and names / Отримати список всіх ID та назв параметрів

**Parameters / Параметри:**
- `language` (optional) - Language code: `uk`, `en`, `ru` (adds translations to `title` field) / Код мови: `uk`, `en`, `ru` (додає переклади в поле `title`)

**Examples / Приклади:**
```bash
# Production / Продакшн
curl https://your-domain.com/api/dump_devm_param_names

# With Ukrainian translations / З українськими перекладами
curl https://your-domain.com/api/dump_devm_param_names?language=uk

# Local access / Локальний доступ
curl http://localhost:8765/api/dump_devm_param_names?language=uk
```

**Response / Відповідь:**
```json
{
  "success": true,
  "params": [
    {
      "id": 19,
      "label": "Information ModBus Port",
      "title": "ModBus порт"
    },
    {
      "id": 21,
      "label": "Information UniqueID",
      "title": "Унікальний ID"
    },
    {
      "id": 37,
      "label": "Information LAN-IP",
      "title": "LAN IP-адреса"
    }
  ],
  "cached": true
}
```

**Note / Примітка:** The `title` field contains the translated name; without `language` the default language (`DATAKOM_LANG`, `uk`) is used. / Поле `title` містить перекладену назву; без `language` використовується мова за замовчуванням (`DATAKOM_LANG`, `uk`).
```

### GET /api/dump_devm_alarm
Get current alarm signals / Отримати поточні аварійні сигнали

**Response / Відповідь:**
```json
{
  "success": true,
  "alarm": {
    "ShutDown": [],
    "LoadDump": [],
    "Warning": [
      {
        "slot": 0,
        "name": "Fuel Filling!",
        "index": 252
      }
    ]
  },
  "cached": true
}
```

### POST /api/device/control
Simulate a controller pushbutton / Імітувати кнопку контролера

Requires header `X-API-Key` — our own service key from `data/control_key` (or env `DATAKOM_CONTROL_KEY`), not a Datakom/SCADA password. How to generate it: [README.md → Remote Control](README.md#remote-control--дистанційне-керування).
Потрібен заголовок `X-API-Key` — власний ключ сервісу з `data/control_key` (або змінної `DATAKOM_CONTROL_KEY`), не пароль Datakom/SCADA. Як згенерувати: [README.md → Дистанційне керування](README.md#remote-control--дистанційне-керування).

**Body / Тіло:** `{"action": "stop" | "auto" | "manual" | "test"}`

```bash
curl -X POST "https://bierdeckel.com.ua/datakom/api/device/control" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"action": "auto"}'
```

The request returns after the controller confirms the command (up to 10 s). The new mode appears in telemetry (param 103) within a few seconds.
Запит повертається після підтвердження контролером (до 10 с). Новий режим з'являється в телеметрії (параметр 103) за кілька секунд.

| HTTP | Response / Відповідь |
|---|---|
| 200 | `{"success": true, "action": "auto", "confirmed_at": "..."}` |
| 400 | Action not allowed / Дія не дозволена (`allowed` lists permitted actions) |
| 401 | Invalid or missing X-API-Key |
| 403 | Control is disabled: no control key configured |
| 502 | `Controller is not connected` / `No confirmation from controller within 10s` / listener unavailable |

`GET /api/health` also reports `control_enabled` and `control_actions`. / також повертає `control_enabled` і `control_actions`.

Command mapping (register `0x2011`, Modbus write via `DKV0MBUS` frame): STOP=1, AUTO=2, MANUAL=4, TEST=8 (GENSET=0x10, MAINS=0x20 disabled by default). Telemetry mode values differ: STOP=1, MANUAL=2, AUTO=4, TEST=8.
Відповідність команд (регістр `0x2011`, запис Modbus у кадрі `DKV0MBUS`): STOP=1, AUTO=2, MANUAL=4, TEST=8. Значення режиму в телеметрії інші: STOP=1, MANUAL=2, AUTO=4, TEST=8.

## Monitoring / Моніторинг

### PM2 Logs / Логи PM2
```bash
# All services / Всі сервіси
pm2 logs

# Specific service / Конкретний сервіс
pm2 logs datakom-api
pm2 logs datakom-listener

# Real-time monitoring / Моніторинг в реальному часі
pm2 monit
```

### Log Files / Файли логів
```
logs/api-out.log       # API stdout
logs/api-error.log     # API stderr
logs/listener-out.log  # Listener stdout
logs/listener-error.log # Listener stderr
```

## Language Settings / Налаштування мови

Default language is Ukrainian (configured in config.py). / За замовчуванням використовується українська мова (налаштовується в config.py).
Change via environment variable / Змінити через змінну оточення:

```bash
# Windows
$env:DATAKOM_LANG="en"  # English
$env:DATAKOM_LANG="uk"  # Ukrainian (default / за замовчуванням)
$env:DATAKOM_LANG="ru"  # Moskalskaya


# Linux
export DATAKOM_LANG=en
```

Or change DEFAULT_LANGUAGE in config.py / Або змінити DEFAULT_LANGUAGE в config.py:
```python
DEFAULT_LANGUAGE = "en"  # or "uk" / або "uk"
```

## Ports / Порти

Ports are configured in **config.py** / Порти налаштовуються в **config.py**:
- **LISTENER_PORT** (default 8760) - TCP listener for Datakom controller / TCP listener для контролера Datakom
- **API_PORT** (default 8765) - HTTP API server / HTTP API сервер

Make sure ports are open in firewall / Переконайтеся, що порти відкриті в файрволі:
```bash
# Linux
sudo ufw allow 8760/tcp
sudo ufw allow 8765/tcp

# Windows
netsh advfirewall firewall add rule name="Datakom Listener" dir=in action=allow protocol=TCP localport=8760
netsh advfirewall firewall add rule name="Datakom API" dir=in action=allow protocol=TCP localport=8765
```

## API Documentation / Документація API

Interactive Swagger documentation / Інтерактивна документація Swagger:
- **http://localhost:8765/docs** - Full API documentation with try-it-out feature / Повна документація API з можливістю тестування

## Troubleshooting / Усунення проблем

### API server won't start / API сервер не запускається
```bash
# Check that port 8765 is free / Перевірити, що порт 8765 вільний
netstat -an | findstr 8765  # Windows
netstat -tulpn | grep 8765  # Linux

# Run manually for debugging / Запустити вручну для налагодження
python api_server.py
```

### Port 8760 not accessible from outside / Порт 8760 недоступний ззовні
```bash
# Check iptables rules / Перевірте правила iptables
sudo iptables -L INPUT -n -v | grep 8760

# If rule missing, add it / Якщо правило відсутнє, додайте його
sudo iptables -I INPUT -p tcp --dport 8760 -j ACCEPT

# Save rules / Збережіть правила
sudo netfilter-persistent save
# або
sudo iptables-save > /etc/iptables/rules.v4

# Test from external computer / Перевірте з зовнішнього комп'ютера
telnet YOUR_SERVER_IP 8760
```

### Listener won't connect / Listener не підключається
```bash
# Check that port 8760 is open / Перевірити, що порт 8760 відкритий
telnet localhost 8760

# Check logs / Перевірити логи
tail -f data/health.json

# Restart listener / Перезапустити listener
pm2 restart datakom-listener
```

### Data not updating / Дані не оновлюються
```bash
# Check listener status / Перевірити статус listener
curl https://your-domain.com/api/health

# Check PM2 logs / Перевірити логи PM2
pm2 logs datakom-listener --lines 50

# Look for connection from controller IP (not 127.0.0.1)
# Шукайте підключення від IP контролера (не 127.0.0.1)
grep "Connection from" logs/listener-out-0.log | grep -v 127.0.0.1
```

### Controller not connecting / Контролер не підключається
**Symptoms / Симптоми:** Only 127.0.0.1 connections in logs / Тільки 127.0.0.1 підключення в логах

**Solution / Рішення:**
1. Check firewall rules / Перевірте правила firewall
2. Verify controller settings: IP=YOUR_SERVER_IP, Port=8760
3. Ensure port 8760 is open in hosting panel / Переконайтеся, що порт 8760 відкритий в панелі хостингу
4. Test connectivity: `telnet YOUR_SERVER_IP 8760` from controller's network

**Note:** API returns cached data if controller is not connected / Примітка: API повертає кешовані дані, якщо контролер не підключений
