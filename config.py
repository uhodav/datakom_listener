"""
Configuration file for Datakom D500 MK3 services
"""
import os

# TCP Listener configuration
LISTENER_HOST = "0.0.0.0"
LISTENER_PORT = 8760

# API Server configuration
API_HOST = "0.0.0.0"
API_PORT = 8765

# Listener rewrites data/health.json at least this often; the API treats an older file as "listener down"
HEALTH_HEARTBEAT_SECONDS = 30
LISTENER_DEAD_AFTER_SECONDS = 90

# Controller sends telemetry about once a minute; older data is reported as stale by the API
TELEMETRY_STALE_SECONDS = int(os.environ.get('DATAKOM_STALE_SECONDS', 300))

# Remote control: the listener accepts commands from the API on a local-only port
CONTROL_HOST = "127.0.0.1"
CONTROL_PORT = 8761
# Command sent while the controller is offline waits this long for it to reconnect
CONTROL_QUEUE_SECONDS = int(os.environ.get('DATAKOM_CONTROL_QUEUE_SECONDS', 120))
# Actions the API may send (genset/mains = load transfer, disabled by default)
CONTROL_ACTIONS = [a.strip() for a in os.environ.get('DATAKOM_CONTROL_ACTIONS', 'stop,auto,manual,test').split(',') if a.strip()]
# API key for control requests: env DATAKOM_CONTROL_KEY or file data/control_key.
# Control is disabled while no key is configured.
CONTROL_KEY_FILE = os.path.join('data', 'control_key')


def get_control_key() -> str:
    key = os.environ.get('DATAKOM_CONTROL_KEY', '').strip()
    if not key and os.path.exists(CONTROL_KEY_FILE):
        with open(CONTROL_KEY_FILE, encoding='utf-8') as f:
            key = f.read().strip()
    return key

# Language settings
# Read from environment variable DATAKOM_LANG or default to 'uk'
DEFAULT_LANGUAGE = os.environ.get('DATAKOM_LANG', 'uk')  # uk, en, ru
