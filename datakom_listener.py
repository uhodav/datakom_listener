import socket
import os
import json
import threading
import traceback
from datetime import datetime
from decoder import decode_telemetry, decode_unknown_offsets
from config import LISTENER_HOST, LISTENER_PORT, HEALTH_HEARTBEAT_SECONDS

HOST = LISTENER_HOST
PORT = LISTENER_PORT

BASE_DIR = "packets"
DATA_DIR = "data"
TELEMETRY_JSON = os.path.join(DATA_DIR, "telemetry.json")
ALERTS_JSON = os.path.join(DATA_DIR, "alerts.json")
UNKNOWN_JSON = os.path.join(DATA_DIR, "unknown_offsets.json")
BLOCKED_IPS_JSON = os.path.join(DATA_DIR, "blocked_ips.json")
HEALTH_JSON = os.path.join(DATA_DIR, "health.json")

DIR_TELEMETRY = os.path.join(BASE_DIR, "telemetry")
DIR_EVENT = os.path.join(BASE_DIR, "event")

DATAKOM_HEADERS = (b"DY0DD500", b"DKV0")
BOT_SIGNATURES = (
    (b"\x16\x03", "TLS handshake"),
    (b"GET ", "HTTP GET"),
    (b"POST ", "HTTP POST"),
    (b"HEAD ", "HTTP HEAD"),
    (b"OPTIONS ", "HTTP OPTIONS"),
)

FIRST_PACKET_TIMEOUT = 10      # seconds to wait for the first packet of a new connection
CONNECTION_TIMEOUT = 300       # seconds of silence before an established connection is dropped
BLOCKED_SAVE_INTERVAL = 60     # seconds between persisting attempt counters of already blocked IPs

for d in (DIR_TELEMETRY, DIR_EVENT, DATA_DIR):
    os.makedirs(d, exist_ok=True)


def write_json_atomic(path: str, payload):
    """Write JSON via a temp file so readers (the API) never see a half-written file"""
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# ---------------------------------------------------------------- health

health_lock = threading.Lock()
health_state = {
    "status": "ok",
    "connect_state": "Disconnected",
    "date_time_change_state": None,
    "last_error": None,
    "last_packet_time": None,
}
active_connections = 0


def update_health(state: str = None, error: dict = None, packet: bool = False):
    """Update health status. Called on state changes, on every packet and by the heartbeat thread,
    so health.json mtime doubles as a liveness signal for the API."""
    with health_lock:
        now = datetime.now().isoformat()
        if state and health_state["connect_state"] != state:
            health_state["connect_state"] = state
            health_state["date_time_change_state"] = now
        if error:
            health_state["last_error"] = error
        if packet:
            health_state["last_packet_time"] = now
        health_state["time"] = now
        write_json_atomic(HEALTH_JSON, health_state)


def heartbeat_loop():
    while True:
        threading.Event().wait(HEALTH_HEARTBEAT_SECONDS)
        try:
            update_health()
        except Exception as e:
            print(f"[!] Heartbeat error: {e}")


# ---------------------------------------------------------------- blocked IPs

blocked_lock = threading.Lock()
blocked_last_save = 0.0


def load_blocked_ips():
    if os.path.exists(BLOCKED_IPS_JSON):
        with open(BLOCKED_IPS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


blocked_ips = load_blocked_ips()


def block_ip(ip, reason, first_packet_hex):
    """Add IP to the blacklist or bump its attempt counter. New entries are persisted immediately,
    counter updates at most once per BLOCKED_SAVE_INTERVAL."""
    global blocked_last_save
    with blocked_lock:
        now = datetime.now()
        if ip not in blocked_ips:
            blocked_ips[ip] = {
                "first_seen": now.isoformat(),
                "reason": reason,
                "first_packet": first_packet_hex,
                "attempts": 1,
                "last_attempt": now.isoformat(),
            }
            print(f"[BLOCK] Added to blacklist: {ip} - {reason}")
            force_save = True
        else:
            blocked_ips[ip]["attempts"] += 1
            blocked_ips[ip]["last_attempt"] = now.isoformat()
            force_save = False

        if force_save or now.timestamp() - blocked_last_save >= BLOCKED_SAVE_INTERVAL:
            write_json_atomic(BLOCKED_IPS_JSON, blocked_ips)
            blocked_last_save = now.timestamp()


def is_ip_blocked(ip):
    with blocked_lock:
        return ip in blocked_ips


# ---------------------------------------------------------------- packets

def classify_packet(data: bytes) -> str:
    if len(data) <= 8:
        return "keepalive"
    if data.startswith(DATAKOM_HEADERS):
        if len(data) >= 600:
            return "telemetry"
        return "keepalive"
    return "event"


def save_packet(directory: str, data: bytes):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = os.path.join(directory, f"pkt_{ts}.txt")
    with open(path, "w", encoding="ascii") as f:
        f.write(data.hex())
    return path


def cleanup_old_packets(directory: str, keep_count: int):
    """Remove old packet files, keeping only the newest 'keep_count' files"""
    try:
        files = []
        for filename in os.listdir(directory):
            if filename.startswith("pkt_") and filename.endswith(".txt"):
                filepath = os.path.join(directory, filename)
                files.append((filepath, os.path.getmtime(filepath)))

        files.sort(key=lambda x: x[1], reverse=True)
        for filepath, _ in files[keep_count:]:
            os.remove(filepath)
    except Exception as e:
        print(f"[!] Error cleaning up {directory}: {e}")


def save_event(data: bytes):
    save_packet(DIR_EVENT, data)
    cleanup_old_packets(DIR_EVENT, 10)


def process_telemetry(data: bytes):
    """Decode a telemetry packet and store telemetry/alerts/unknown offsets JSON"""
    path = save_packet(DIR_TELEMETRY, data)
    cleanup_old_packets(DIR_TELEMETRY, 20)
    now = datetime.now().isoformat()

    decoded = decode_telemetry(data)
    alerts = decoded.pop("_alerts_internal", {"shutDown": [], "warning": [], "loadDump": []})
    decoded["timestamp"] = now
    decoded["raw_packet_file"] = os.path.basename(path)
    write_json_atomic(TELEMETRY_JSON, decoded)
    write_json_atomic(ALERTS_JSON, alerts)

    unknown = decode_unknown_offsets(data)
    unknown["timestamp"] = now
    unknown["raw_packet_file"] = os.path.basename(path)
    write_json_atomic(UNKNOWN_JSON, unknown)


def handle_packet(data: bytes):
    pkt_type = classify_packet(data)
    if pkt_type == "telemetry":
        process_telemetry(data)
    elif pkt_type == "event":
        save_event(data)


def bot_reason(data: bytes):
    for signature, reason in BOT_SIGNATURES:
        if data.startswith(signature):
            return reason
    return None


# ---------------------------------------------------------------- connections

def handle_connection(conn: socket.socket, addr):
    global active_connections
    client_ip = addr[0]
    registered = False
    try:
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        conn.settimeout(FIRST_PACKET_TIMEOUT)

        try:
            first_data = conn.recv(4096)
        except socket.timeout:
            print(f"[!] Timeout after {FIRST_PACKET_TIMEOUT}s from {client_ip} (could be slow router/controller)")
            return

        if not first_data:
            print(f"[!] Empty connection from {addr}, closing")
            return

        reason = bot_reason(first_data)
        if reason is None and not (first_data.startswith(DATAKOM_HEADERS) or len(first_data) <= 8):
            reason = f"Unknown protocol: {first_data[:20].hex()}"
        if reason:
            save_event(first_data)
            block_ip(client_ip, reason, first_data[:64].hex())
            return

        # Valid Datakom connection
        conn.settimeout(CONNECTION_TIMEOUT)
        print(f"[OK] Valid Datakom connection from {addr}")
        with health_lock:
            active_connections += 1
        registered = True
        update_health("Connected", packet=True)

        data = first_data
        while data:
            if bot_reason(data):
                print(f"[http] request ignored from {client_ip}")
                save_event(data)
                break

            conn.sendall(data[:8])
            handle_packet(data)
            update_health(packet=True)
            data = conn.recv(4096)

        print(f"[*] Datakom connection closed by {addr}")
        if registered:
            update_health("Disconnected")

    except (TimeoutError, socket.timeout) as e:
        print(f"[!] Connection timeout from {addr}: no data for {CONNECTION_TIMEOUT}s")
        update_health("Timeout", {
            "timestamp": datetime.now().isoformat(),
            "message": str(e),
            "code": "TIMEOUT",
        })
    except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError) as e:
        print(f"[!] Connection lost from {addr}: {e}")
        update_health("Disconnected", {
            "timestamp": datetime.now().isoformat(),
            "message": str(e),
            "code": "CONNECTION_LOST",
        })
    except Exception as e:
        print(f"[!] Error handling {addr}: {e}")
        update_health("Error", {
            "timestamp": datetime.now().isoformat(),
            "message": str(e),
            "code": "UNKNOWN_ERROR",
            "stack": traceback.format_exc(),
        })
    finally:
        try:
            conn.close()
        except OSError:
            pass
        if registered:
            with health_lock:
                active_connections -= 1
                still_connected = active_connections > 0
            if not still_connected and health_state["connect_state"] == "Connected":
                update_health("Listening")


def main():
    if blocked_ips:
        print(f"[INFO] Loaded {len(blocked_ips)} blocked IP addresses")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(5)

    # Write health only after bind succeeded, so a duplicate instance can't fake liveness
    update_health("Listening")
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    print(f"[+] Listening on {HOST}:{PORT}")

    try:
        while True:
            conn, addr = sock.accept()
            if is_ip_blocked(addr[0]):
                block_ip(addr[0], blocked_ips[addr[0]]["reason"], "")
                conn.close()
                continue
            threading.Thread(target=handle_connection, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        update_health("Stopped")
    finally:
        with blocked_lock:
            write_json_atomic(BLOCKED_IPS_JSON, blocked_ips)
        sock.close()


if __name__ == "__main__":
    main()
