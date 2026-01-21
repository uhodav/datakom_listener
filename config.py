"""
Configuration file for Datakom D500 MK3 services
"""
import os

# TCP Listener configuration
LISTENER_HOST = "0.0.0.0"
LISTENER_PORT = 3333

# API Server configuration
API_HOST = "0.0.0.0"
API_PORT = 7777

# Language settings
# Read from environment variable DATAKOM_LANG or default to 'uk'
DEFAULT_LANGUAGE = os.environ.get('DATAKOM_LANG', 'uk')  # uk, en, ru
