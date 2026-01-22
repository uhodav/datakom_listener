"""
Datakom D500 MK3 REST API Server
Provides HTTP API access to telemetry data collected by datakom_listener
"""

import os
import json
import subprocess
import psutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from config import API_HOST, API_PORT, DEFAULT_LANGUAGE
from param_mapping import get_param_id_label, get_all_param_names
import importlib

app = FastAPI(
    title="Datakom D500 MK3 API",
    version="1.0.0",
    redoc_url=None  # Disable ReDoc, only use Swagger /docs
)

# Paths
DATA_DIR = Path("data")
TELEMETRY_JSON = DATA_DIR / "telemetry.json"
ALERTS_JSON = DATA_DIR / "alerts.json"
HEALTH_JSON = DATA_DIR / "health.json"

# Listener process management
LISTENER_SCRIPT = "datakom_listener.py"
listener_process: Optional[subprocess.Popen] = None
listener_status_cache = {"running": False, "last_check": 0}
CACHE_TTL = 1.0  # Cache status for 1 second


def load_language_module(lang_code: str):
    """Load language module dynamically"""
    try:
        return importlib.import_module(f"lang.{lang_code}")
    except ImportError:
        # Fallback to default language
        return importlib.import_module(f"lang.{DEFAULT_LANGUAGE}")


def get_param_title(label: str, lang_code: str = None) -> str:
    """Get translated title for parameter label"""
    if not lang_code:
        lang_code = DEFAULT_LANGUAGE
    
    lang_module = load_language_module(lang_code)
    
    # Try to find translation in PARAM_TITLES if exists
    if hasattr(lang_module, 'PARAM_TITLES'):
        return lang_module.PARAM_TITLES.get(label, "")
    
    return ""


def get_value_hint(label: str, value, lang_code: str = None) -> str:
    """Get text description for numeric value from language dictionaries"""
    if not isinstance(value, (int, float)):
        return ""
    
    if not lang_code:
        lang_code = DEFAULT_LANGUAGE
    
    lang_module = load_language_module(lang_code)
    
    # Map labels to dictionary names
    label_to_dict = {
        "Genset Mode": "MODE_NAMES",
        "Genset State": "STATE_NAMES",
        "Engine State": "ENGINE_STATE_NAMES",
        "Breaker State": "BREAKER_STATE_NAMES",
        "Mains State": "MAINS_STATE_NAMES",
        "Battery State": "BATTERY_STATE_NAMES",
        "Start Source": "START_SOURCE_NAMES",
        "Running Type": "RUNNING_TYPE_NAMES",
    }
    
    dict_name = label_to_dict.get(label)
    if dict_name and hasattr(lang_module, dict_name):
        value_dict = getattr(lang_module, dict_name)
        return value_dict.get(int(value), "")
    
    return ""


def is_listener_running() -> bool:
    """Check if listener process is running (optimized with caching)"""
    global listener_process, listener_status_cache
    
    # Use cached result if fresh (< 1 second old)
    import time
    now = time.time()
    if now - listener_status_cache["last_check"] < CACHE_TTL:
        return listener_status_cache["running"]
    
    # Check our subprocess first (if started by this API)
    if listener_process and listener_process.poll() is None:
        listener_status_cache.update({"running": True, "last_check": now})
        return True
    
    # For PM2-managed processes, check health.json timestamp
    # If file was updated recently (within 60 seconds), listener is alive
    try:
        if HEALTH_JSON.exists():
            file_mtime = HEALTH_JSON.stat().st_mtime
            age_seconds = now - file_mtime
            
            # If health.json updated within last 60 seconds, listener is running
            is_running = (age_seconds < 60)
            listener_status_cache.update({"running": is_running, "last_check": now})
            return is_running
    except Exception as e:
        print(f"Error checking listener health file: {e}")
    
    # Fallback: try to connect to listener port
    try:
        import socket
        from config import LISTENER_PORT
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex(('127.0.0.1', LISTENER_PORT))
        sock.close()
        
        is_running = (result == 0)
        listener_status_cache.update({"running": is_running, "last_check": now})
        return is_running
    except Exception as e:
        print(f"Error checking listener port: {e}")
        listener_status_cache.update({"running": False, "last_check": now})
        return False


def start_listener() -> bool:
    """Start listener process if not running"""
    global listener_process
    
    if is_listener_running():
        return True
    
    try:
        # Use python3 on Linux, python on Windows
        python_cmd = "python" if os.name == 'nt' else "python3"
        listener_process = subprocess.Popen(
            [python_cmd, LISTENER_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        return True
    except Exception as e:
        print(f"Failed to start listener: {e}")
        return False


def load_health() -> dict:
    """Load health status from file or generate default"""
    if HEALTH_JSON.exists():
        with open(HEALTH_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return {
        "status": "unknown",
        "time": datetime.now().isoformat(),
        "connect_state": "Unknown",
        "date_time_change_state": None,
        "reconnect_wait_minutes": 0,
        "next_reconnect_time": None,
        "last_error": None
    }


def load_telemetry() -> dict:
    """Load latest telemetry data"""
    if TELEMETRY_JSON.exists():
        with open(TELEMETRY_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_alerts() -> dict:
    """Load current alerts"""
    if ALERTS_JSON.exists():
        with open(ALERTS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"shutDown": [], "loadDump": [], "warning": []}


def telemetry_to_params(telemetry: dict, lang_code: str = None) -> List[dict]:
    """Convert telemetry JSON to parameter list with fixed IDs"""
    params = []
    
    for key, value_obj in telemetry.items():
        if key in ('timestamp', 'raw_packet_file', '_alerts_internal'):
            continue
        
        if isinstance(value_obj, dict) and 'value' in value_obj:
            param_id, label = get_param_id_label(key)
            
            # Skip unmapped parameters (id=0)
            if param_id == 0:
                continue
            
            value = value_obj['value']
            param = {
                "id": param_id,
                "label": label,
                "labelHint": get_param_title(label, lang_code or DEFAULT_LANGUAGE),
                "value": value,
                "valueHint": get_value_hint(label, value, lang_code or DEFAULT_LANGUAGE),
                "unit": value_obj.get('unit', ''),
            }
            params.append(param)
    
    # Sort by ID for consistent output
    params.sort(key=lambda x: x['id'])
    
    return params


@app.get("/api_test.html")
async def api_test_page():
    """Serve API test HTML page"""
    return FileResponse("api_test.html")


@app.get("/api/health")
async def get_health():
    """Server health check"""
    listener_running = is_listener_running()
    health = load_health()
    
    health["listener_running"] = listener_running
    health["status"] = "ok" if listener_running else "listener_stopped"
    health["time"] = datetime.now().isoformat()
    
    if not listener_running:
        health["connect_state"] = "Stopped"
    elif health.get("connect_state") in ("Unknown", None, "Disconnected", "Stopped") and listener_running:
        # If listener is running but state indicates it's not active, update to "Listening"
        # This handles cases where health.json has stale "Stopped" status from previous run
        health["connect_state"] = "Listening"
    
    return health


@app.get("/api/dump_devm")
async def get_parameters(
    id: Optional[str] = Query(None, description="Comma-separated parameter IDs"),
    language: Optional[str] = Query(None, description="Language code: uk, en, ru")
):
    """Get device parameters (all or filtered by id)"""
    
    # Ensure listener is running
    listener_running = is_listener_running()
    if not listener_running:
        start_listener()
    
    telemetry = load_telemetry()
    all_params = telemetry_to_params(telemetry, language)
    
    # Filter by IDs if specified
    if id:
        requested_ids = [int(x.strip()) for x in id.split(',')]
        filtered_params = [p for p in all_params if p['id'] in requested_ids]
        result_params = filtered_params
    else:
        result_params = all_params
    
    return {
        "success": True,
        "result": result_params,
        "cached": True,
        "timestamp": telemetry.get('timestamp', datetime.now().isoformat())
    }


@app.get("/api/dump_devm_param_names")
async def get_parameter_names(language: Optional[str] = Query(None, description="Language code: uk, en, ru")):
    """Get all parameter IDs and labels"""
    
    # Return all defined parameter names from mapping
    param_names = get_all_param_names()
    
    # Add title field with translation if language specified
    if language:
        for param in param_names:
            param['title'] = get_param_title(param['label'], language)
    else:
        for param in param_names:
            param['title'] = ""
    
    return {
        "success": True,
        "params": param_names,
        "cached": True
    }


@app.get("/api/dump_devm_alarm")
async def get_alarms():
    """Get current alarm states"""
    
    # Ensure listener is running
    listener_running = is_listener_running()
    if not listener_running:
        start_listener()
    
    alerts = load_alerts()
    
    # Convert to API format with capital letters
    alarm_data = {
        "ShutDown": alerts.get("shutDown", []),
        "LoadDump": alerts.get("loadDump", []),
        "Warning": alerts.get("warning", [])
    }
    
    return {
        "success": True,
        "alarm": alarm_data,
        "cached": True
    }


@app.on_event("startup")
async def startup_event():
    """Ensure data directory exists on startup"""
    DATA_DIR.mkdir(exist_ok=True)
    
    # Start listener if not running
    if not is_listener_running():
        start_listener()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global listener_process
    if listener_process and listener_process.poll() is None:
        listener_process.terminate()
        listener_process.wait(timeout=5)


if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")
