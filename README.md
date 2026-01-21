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
pip install -r requirements.txt

# Install PM2 / Встановити PM2
npm install -g pm2

# Create required directories / Створити необхідні директорії
mkdir data packets packets\telemetry packets\event logs
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
LISTENER_PORT = 3333  # TCP port for controller / TCP порт для контролера
API_PORT = 7777       # HTTP API port / HTTP API порт
DEFAULT_LANGUAGE = "uk"  # Default language: uk, en / Мова за замовчуванням
```

## API Documentation / Документація API

- **Full documentation / Повна документація:** [README_API.md](README_API.md)
- **PM2 deployment / Розгортання PM2:** [README_PM2.md](README_PM2.md)
- **Swagger UI:** http://localhost:7777/docs
- **API test page / Тестова сторінка:** http://localhost:7777/api_test.html

## API Endpoints

- `GET /api/health` - System health check / Перевірка стану системи
- `GET /api/dump_devm?id=IDs&language=LANG` - Get parameters / Отримати параметри
- `GET /api/dump_devm_param_names?language=LANG` - Get parameter list / Отримати список параметрів
- `GET /api/dump_devm_alarm` - Get alarms / Отримати аварії

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
