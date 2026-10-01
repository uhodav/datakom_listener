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

# Language settings
# Read from environment variable DATAKOM_LANG or default to 'uk'
DEFAULT_LANGUAGE = os.environ.get('DATAKOM_LANG', 'uk')  # uk, en, ru
