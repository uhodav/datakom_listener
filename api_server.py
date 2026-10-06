"""
Datakom D500 MK3 REST API Server
Provides HTTP API access to telemetry data collected by datakom_listener
"""

import hmac
import json
import importlib
import socket
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from fastapi import Body, FastAPI, Header, Query, Request
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
from config import (API_HOST, API_PORT, DEFAULT_LANGUAGE,
                    LISTENER_DEAD_AFTER_SECONDS, TELEMETRY_STALE_SECONDS,
                    CONTROL_HOST, CONTROL_PORT, CONTROL_ACTIONS, get_control_key)
from param_mapping import get_param_id_label, get_all_param_names

# Paths
DATA_DIR = Path("data")
TELEMETRY_JSON = DATA_DIR / "telemetry.json"
ALERTS_JSON = DATA_DIR / "alerts.json"
HEALTH_JSON = DATA_DIR / "health.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA_DIR.mkdir(exist_ok=True)
    yield


app = FastAPI(
    title="Datakom D500 MK3 API",
    version="1.0.0",
    redoc_url=None,  # Disable ReDoc, only use Swagger /docs
    lifespan=lifespan,
)


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
    """Listener is managed by PM2 and rewrites health.json every HEALTH_HEARTBEAT_SECONDS,
    so a fresh file means the process is alive."""
    try:
        return time.time() - HEALTH_JSON.stat().st_mtime < LISTENER_DEAD_AFTER_SECONDS
    except FileNotFoundError:
        return False


def load_json(path: Path, default):
    """Read a JSON file written by the listener; fall back to default if missing or unreadable"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except (OSError, ValueError) as e:
        print(f"Failed to read {path}: {e}")
        return default


def load_health() -> dict:
    """Load health status from file or generate default"""
    return load_json(HEALTH_JSON, {
        "status": "unknown",
        "connect_state": "Unknown",
        "date_time_change_state": None,
        "last_error": None,
    })


def load_telemetry() -> dict:
    """Load latest telemetry data"""
    return load_json(TELEMETRY_JSON, {})


def load_alerts() -> dict:
    """Load current alerts"""
    return load_json(ALERTS_JSON, {"shutDown": [], "loadDump": [], "warning": []})


def telemetry_age_seconds(telemetry: dict) -> Optional[int]:
    """Seconds since the telemetry packet was received, None if there is no telemetry"""
    ts = telemetry.get('timestamp')
    if not ts:
        return None
    try:
        return int((datetime.now() - datetime.fromisoformat(ts)).total_seconds())
    except ValueError:
        return None


def freshness(telemetry: dict) -> dict:
    """Fields telling clients whether cached data is still current"""
    age = telemetry_age_seconds(telemetry)
    return {
        "data_age_seconds": age,
        "stale": age is None or age > TELEMETRY_STALE_SECONDS,
    }


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

    # Last update = when the server received the packet (decoder only knows the controller clock)
    ts = telemetry.get('timestamp')
    if ts:
        param_id, label = get_param_id_label('last_update_date')
        params.append({
            "id": param_id,
            "label": label,
            "labelHint": get_param_title(label, lang_code or DEFAULT_LANGUAGE),
            "value": ts[:19].replace('T', ' '),
            "valueHint": "",
            "unit": "",
        })

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
    telemetry = load_telemetry()

    health["listener_running"] = listener_running
    health["status"] = "ok" if listener_running else "listener_stopped"
    health["time"] = datetime.now().isoformat()
    health["telemetry_timestamp"] = telemetry.get('timestamp')
    health.update(freshness(telemetry))

    if not listener_running:
        health["connect_state"] = "Stopped"
    elif health.get("connect_state") in ("Unknown", None, "Stopped"):
        health["connect_state"] = "Listening"

    health["control_enabled"] = bool(get_control_key())
    health["control_actions"] = CONTROL_ACTIONS

    return health


def send_to_listener(action: str, source: str) -> dict:
    """Forward a control action to the listener's local control port and wait for its result"""
    try:
        with socket.create_connection((CONTROL_HOST, CONTROL_PORT), timeout=40) as sock:
            sock.sendall(json.dumps({"action": action, "source": source}).encode("utf-8"))
            response = b""
            while not response.endswith(b"\n"):
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
        return json.loads(response.decode("utf-8"))
    except (OSError, ValueError) as e:
        return {"success": False, "error": f"Listener control port unavailable: {e}"}


@app.post("/api/device/control")
def device_control(
    request: Request,
    body: dict = Body(..., examples=[{"action": "stop"}]),
    x_api_key: Optional[str] = Header(None),
):
    """Simulate a controller pushbutton (stop, auto, manual, test). Requires X-API-Key."""
    key = get_control_key()
    if not key:
        return JSONResponse({"success": False, "error": "Control is disabled: no control key configured"}, status_code=403)
    if not x_api_key or not hmac.compare_digest(x_api_key, key):
        return JSONResponse({"success": False, "error": "Invalid or missing X-API-Key"}, status_code=401)

    action = str(body.get("action") or body.get("command") or "").lower()
    if action not in CONTROL_ACTIONS:
        return JSONResponse({"success": False, "error": f"Action not allowed: {action}",
                             "allowed": CONTROL_ACTIONS}, status_code=400)

    source = request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for") or request.client.host
    print(f"[CMD] {action.upper()} requested from {source}")
    result = send_to_listener(action, source)
    status_code = (202 if result.get("queued") else 200) if result.get("success") else 502
    return JSONResponse(result, status_code=status_code)


@app.get("/api/dump_devm")
async def get_parameters(
    id: Optional[str] = Query(None, description="Comma-separated parameter IDs"),
    language: Optional[str] = Query(None, description="Language code: uk, en, ru")
):
    """Get device parameters (all or filtered by id)"""
    telemetry = load_telemetry()
    all_params = telemetry_to_params(telemetry, language)

    # Filter by IDs if specified
    if id:
        try:
            requested_ids = {int(x) for x in id.split(',') if x.strip()}
        except ValueError:
            return {"success": False, "error": f"Invalid id list: {id}"}
        result_params = [p for p in all_params if p['id'] in requested_ids]
    else:
        result_params = all_params

    return {
        "success": True,
        "result": result_params,
        "cached": True,
        "timestamp": telemetry.get('timestamp', datetime.now().isoformat()),
        **freshness(telemetry),
    }


@app.get("/api/dump_devm_param_names")
async def get_parameter_names(language: Optional[str] = Query(None, description="Language code: uk, en, ru")):
    """Get all parameter IDs and labels"""
    param_names = get_all_param_names()

    for param in param_names:
        param['title'] = get_param_title(param['label'], language or DEFAULT_LANGUAGE)

    return {
        "success": True,
        "params": param_names,
        "cached": True
    }


@app.get("/api/dump_devm_alarm")
async def get_alarms(language: Optional[str] = Query(None, description="Language code: uk, en, ru")):
    """Get current alarm states"""
    alerts = load_alerts()

    lang_module = load_language_module(language or DEFAULT_LANGUAGE)
    alarm_messages = lang_module.ALARM_MESSAGES

    def translate_alarms(alarm_list):
        return [alarm_messages.get(idx, f"Alarm #{idx}") for idx in alarm_list]

    return {
        "success": True,
        "alarm": {
            "ShutDown": translate_alarms(alerts.get("shutDown", [])),
            "LoadDump": translate_alarms(alerts.get("loadDump", [])),
            "Warning": translate_alarms(alerts.get("warning", []))
        },
        "cached": True,
        **freshness(load_telemetry()),
    }


if __name__ == "__main__":
    # Access log disabled: clients poll every parameter separately and it produced ~25 MB/day;
    # nginx already keeps access logs for /datakom/api/
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info", access_log=False)
