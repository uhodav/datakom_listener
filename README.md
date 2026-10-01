[![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/badges/StandWithUkraine.svg)](https://stand-with-ukraine.pp.ua)

#### Ukraine is still suffering from Russian aggression, [please consider supporting Red Cross Ukraine with a donation](https://redcross.org.ua/en/).

[![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner2-direct.svg)](https://stand-with-ukraine.pp.ua)

# Datakom D500 MK3 Telemetry System

REST API server for Datakom D500 MK3 generator controller telemetry monitoring.
REST API сервер для моніторингу телеметрії контролера генератора Datakom D500 MK3.

## Project Structure / Структура проекту

```
datakom_listener/
├── api_server.py           # REST API server / REST API сервер
├── datakom_listener.py     # TCP listener for controller / TCP слухач для контролера
├── decoder.py              # Binary packet decoder / Декодер бінарних пакетів
├── config.py               # Configuration / Конфігурація
├── param_mapping.py        # Parameter ID mapping / Маппінг ID параметрів
├── datakom_constants.py    # Protocol constants / Константи протоколу
├── requirements.txt        # Python dependencies / Python залежності
├── ecosystem.config.js     # PM2 configuration / Конфігурація PM2
├── api_test.html          # API test page / Тестова сторінка API
├── lang/                  # Language translations / Мовні переклади
│   ├── uk.py             # Ukrainian / Українська
│   ├── en.py             # English / Англійська
│   └── ru.py             # Russian / Російська
├── data/                 # Runtime data (not in Git) / Робочі дані (не в Git)
│   ├── telemetry.json   # Latest telemetry / Остання телеметрія
│   ├── alerts.json      # Current alerts / Поточні аварії
│   └── health.json      # System health / Стан системи
├── packets/             # Saved packets (not in Git) / Збережені пакети (не в Git)
│   ├── telemetry/      # Telemetry packets / Пакети телеметрії
│   └── event/          # Event packets / Пакети подій
└── logs/               # PM2 logs (not in Git) / Логи PM2 (не в Git)
```

## Quick Start / Швидкий старт

### Installation / Встановлення

```bash
# Install Python dependencies / Встановити Python залежності
# If pip3 is not installed, use: / Якщо pip3 не встановлено, використайте:
python3 -m pip install -r requirements.txt

# Or install pip3 first (Ubuntu/Debian): / Або спочатку встановіть pip3 (Ubuntu/Debian):
# sudo apt update && sudo apt install python3-pip
# pip3 install -r requirements.txt

# Install PM2 (requires Node.js) / Встановити PM2 (потрібен Node.js)
npm install -g pm2

# Create required directories / Створити необхідні директорії
mkdir -p data packets/telemetry packets/event logs
```

### Running / Запуск

```bash
# Start services / Запустити сервіси
pm2 start ecosystem.config.js

# Save and configure autostart / Зберегти та налаштувати автозапуск
pm2 save
pm2 startup

# View status / Переглянути статус
pm2 status

# View logs / Переглянути логи
pm2 logs
```

## Configuration / Конфігурація

Edit `config.py` / Редагувати `config.py`:

```python
LISTENER_PORT = 8760  # TCP port for controller / TCP порт для контролера
API_PORT = 8765       # HTTP API port / HTTP API порт
DEFAULT_LANGUAGE = "uk"  # Default language: uk, en / Мова за замовчуванням
```

## API Documentation / Документація API

- **Full documentation / Повна документація:** [README_API.md](README_API.md)
- **PM2 deployment / Розгортання PM2:** [README_PM2.md](README_PM2.md)
- **Swagger UI:** http://localhost:8765/docs
- **API test page / Тестова сторінка:** http://localhost:8765/api_test.html

## API Endpoints

- `GET /api/health` - System health check / Перевірка стану системи
- `GET /api/dump_devm?id=IDs&language=LANG` - Get parameters / Отримати параметри
- `GET /api/dump_devm_param_names?language=LANG` - Get parameter list / Отримати список параметрів
- `GET /api/dump_devm_alarm` - Get alarms / Отримати аварії
- `POST /api/device/control` - Controller pushbutton (STOP/AUTO/MANUAL/TEST), requires `X-API-Key` / Кнопка контролера, потрібен `X-API-Key`

## Remote Control / Дистанційне керування

The API can simulate controller pushbuttons (STOP, AUTO, MANUAL, TEST). The command is sent to the controller over its own connection to the listener (port 8760); the controller echoes it back as confirmation.
API може імітувати кнопки контролера (STOP, AUTO, MANUAL, TEST). Команда надсилається контролеру через його ж з'єднання з listener (порт 8760), контролер підтверджує її відповіддю.

**Control key / Ключ керування.** Control requests require the `X-API-Key` header. This is our own key checked only by `api_server.py` — it is not a Datakom / Rainbow / SCADA password. One key for the whole service (not bound to a user). While no key is configured, control is disabled (HTTP 403).
Запити керування потребують заголовка `X-API-Key`. Це наш власний ключ, його перевіряє лише `api_server.py` — це не пароль Datakom / Rainbow / SCADA. Один ключ на весь сервіс (не прив'язаний до користувача). Поки ключ не задано, керування вимкнено (HTTP 403).

Generate the key on the server / Згенерувати ключ на сервері:
```bash
cd /path/to/datakom_listener
python3 -c 'import secrets;print(secrets.token_urlsafe(24))' > data/control_key && chmod 600 data/control_key
cat data/control_key
```
- The key is static: it survives restarts and deployments (`data/` is gitignored and not overwritten). / Ключ постійний: зберігається після перезапусків і викладок (`data/` не в git і не перезаписується).
- To rotate, run the command again — takes effect immediately, no restart. To disable control, delete the file. / Щоб змінити — виконайте команду ще раз, діє одразу без перезапуску. Щоб вимкнути керування — видаліть файл.
- Alternative: environment variable `DATAKOM_CONTROL_KEY` (takes precedence over the file). / Альтернатива: змінна оточення `DATAKOM_CONTROL_KEY` (має пріоритет над файлом).
- Allowed actions: `DATAKOM_CONTROL_ACTIONS` (default `stop,auto,manual,test`; `genset`/`mains` — load transfer — are disabled by default). / Дозволені дії: `DATAKOM_CONTROL_ACTIONS` (за замовчуванням `stop,auto,manual,test`; `genset`/`mains` — перемикання навантаження — вимкнені).

Where to enter the key / Де вказати ключ:
- `api_test.html` → block "Керування контроллером" → field "Ключ керування" (kept only for the browser tab session). / блок «Керування контроллером» → поле «Ключ керування» (зберігається лише на час сесії вкладки).
- Home Assistant integration → settings → "Control key"; without it control buttons are not created. / Інтеграція Home Assistant → налаштування → «Ключ керування»; без нього кнопки керування не створюються.
- Any HTTP client: header `X-API-Key: <key>`. See [README_API.md](README_API.md#post-apidevicecontrol). / Будь-який HTTP-клієнт: заголовок `X-API-Key: <ключ>`.

After a listener restart the controller needs ~1-2 minutes to reconnect; until then commands return `Controller is not connected`.
Після перезапуску listener контролеру потрібно ~1-2 хвилини, щоб перепідключитися; до того команди повертають `Controller is not connected`.

## Features / Особливості

- ✅ Real-time telemetry monitoring / Моніторинг телеметрії в реальному часі
- ✅ REST API with Swagger documentation / REST API з Swagger документацією
- ✅ Multi-language support (Ukrainian, English) / Багатомовна підтримка (українська, англійська)
- ✅ Automatic packet cleanup / Автоматичне очищення пакетів
- ✅ Bot protection / Захист від ботів
- ✅ PM2 process management / Управління процесами через PM2
- ✅ Health monitoring / Моніторинг стану

## Requirements / Вимоги

- Python 3.11+
- Node.js 16+ (for PM2 / для PM2)
- Windows/Linux/macOS

## License / Ліцензія

Proprietary / Власницька

## Support / Підтримка

For technical support / Технічна підтримка: see documentation files
