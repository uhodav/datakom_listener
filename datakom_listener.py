import socket
import os
import json
from datetime import datetime
from decoder import decode_telemetry, decode_unknown_offsets, format_telemetry
from config import LISTENER_HOST, LISTENER_PORT

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

for d in (DIR_TELEMETRY, DIR_EVENT, DATA_DIR):
    os.makedirs(d, exist_ok=True)

keepalive_counter = 0

# Health tracking
health_state = {
    "status": "ok",
    "connect_state": "Disconnected",
    "date_time_change_state": None,
    "last_error": None
}

def update_health(state: str, error: dict = None):
    """Update health status"""
    global health_state
    if health_state["connect_state"] != state:
        health_state["connect_state"] = state
        health_state["date_time_change_state"] = datetime.now().isoformat()
    
    if error:
        health_state["last_error"] = error
    
    health_state["time"] = datetime.now().isoformat()
    
    with open(HEALTH_JSON, "w", encoding="utf-8") as f:
        json.dump(health_state, f, indent=2, ensure_ascii=False)

# Load blocked IPs database
def load_blocked_ips():
    if os.path.exists(BLOCKED_IPS_JSON):
        with open(BLOCKED_IPS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_blocked_ips(blocked_ips):
    with open(BLOCKED_IPS_JSON, "w", encoding="utf-8") as f:
        json.dump(blocked_ips, f, indent=2, ensure_ascii=False)

def block_ip(ip, reason, first_packet_hex):
    blocked_ips = load_blocked_ips()
    
    if ip not in blocked_ips:
        blocked_ips[ip] = {
            "first_seen": datetime.now().isoformat(),
            "reason": reason,
            "first_packet": first_packet_hex,
            "attempts": 1,
            "last_attempt": datetime.now().isoformat()
        }
        print(f"[BLOCK] Added to blacklist: {ip} - {reason}")
    else:
        blocked_ips[ip]["attempts"] += 1
        blocked_ips[ip]["last_attempt"] = datetime.now().isoformat()
        print(f"[BLOCK] Repeat attempt from {ip} (attempt #{blocked_ips[ip]['attempts']})")
    
    save_blocked_ips(blocked_ips)
    return blocked_ips[ip]["attempts"]

def is_ip_blocked(ip):
    blocked_ips = load_blocked_ips()
    return ip in blocked_ips

# Print blocked IPs summary on startup
blocked_ips = load_blocked_ips()
if blocked_ips:
    print(f"[INFO] Loaded {len(blocked_ips)} blocked IP addresses")
    for ip, info in list(blocked_ips.items())[:5]:
        print(f"    {ip}: {info['reason']} (attempts: {info['attempts']})")
    if len(blocked_ips) > 5:
        print(f"    ... and {len(blocked_ips) - 5} more")

# Initialize health status on startup
update_health("Listening")


def classify_packet(data: bytes) -> str:
    if len(data) <= 8:
        return "keepalive"
    if data.startswith(b"DY0DD500") or data.startswith(b"DKV0"):
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
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x[1], reverse=True)
        
        # Remove files beyond keep_count
        for filepath, _ in files[keep_count:]:
            os.remove(filepath)
            
    except Exception as e:
        print(f"[!] Error cleaning up {directory}: {e}")


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((HOST, PORT))
sock.listen(5)

print(f"[+] Listening on {HOST}:{PORT}")

while True:
    try:
        conn, addr = sock.accept()
        
        client_ip = addr[0]
        
        # CHECK IF IP IS ALREADY BLOCKED
        if is_ip_blocked(client_ip):
            blocked_ips = load_blocked_ips()
            attempts = blocked_ips[client_ip]["attempts"]
            reason = blocked_ips[client_ip]["reason"]
            print(f"[BLOCKED] IP {client_ip} attempting connection (attempt #{attempts}, reason: {reason})")
            
            # Update attempts counter
            block_ip(client_ip, reason, "")
            
            conn.close()
            continue
        
        # Enable TCP keepalive to detect dead connections
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        
        # Timeout for first packet - increased for slow controllers
        conn.settimeout(10)
        
        print(f"[+] Connection from {addr}")
        
        # Read first packet to identify connection type
        try:
            print(f"[DEBUG] Waiting for data from {client_ip} (timeout 10s)...")
            first_data = conn.recv(4096)
            
            if not first_data:
                print(f"[!] Empty connection from {addr}, closing")
                conn.close()
                continue
            
            print(f"[DEBUG] Received {len(first_data)} bytes from {client_ip}")
            print(f"[DEBUG] First 32 bytes (hex): {first_data[:32].hex()}")
            print(f"[DEBUG] First 32 bytes (ascii): {''.join(chr(b) if 32 <= b <= 126 else '.' for b in first_data[:32])}")
                
            # Check if it's HTTP/TLS bot traffic
            if first_data.startswith(b'GET ') or first_data.startswith(b'POST ') or \
               first_data.startswith(b'HEAD ') or first_data.startswith(b'OPTIONS ') or \
               first_data.startswith(b'\x16\x03'):  # TLS handshake
                
                # Determine bot type
                if first_data.startswith(b'\x16\x03'):
                    reason = "TLS handshake"
                elif first_data.startswith(b'GET '):
                    reason = "HTTP GET"
                elif first_data.startswith(b'POST '):
                    reason = "HTTP POST"
                elif first_data.startswith(b'HEAD '):
                    reason = "HTTP HEAD"
                elif first_data.startswith(b'OPTIONS '):
                    reason = "HTTP OPTIONS"
                else:
                    reason = "HTTP/TLS bot"
                
                print(f"[!] Bot detected from {client_ip}: {reason}")
                save_packet(DIR_EVENT, first_data)
                cleanup_old_packets(DIR_EVENT, 10)
                
                # Add to blocked list
                first_packet_hex = first_data[:64].hex()
                block_ip(client_ip, reason, first_packet_hex)
                
                conn.close()
                continue
            
            # Check if it's Datakom protocol
            if not (first_data.startswith(b"DY0DD500") or first_data.startswith(b"DKV0") or len(first_data) <= 8):
                print(f"[!] Unknown protocol from {client_ip}, dropping connection")
                print(f"    First bytes: {first_data[:20].hex()}")
                save_packet(DIR_EVENT, first_data)
                cleanup_old_packets(DIR_EVENT, 10)
                
                # Add to blocked list
                reason = f"Unknown protocol: {first_data[:20].hex()}"
                first_packet_hex = first_data[:64].hex()
                block_ip(client_ip, reason, first_packet_hex)
                
                conn.close()
                continue
                
            # Valid Datakom connection - extend timeout
            conn.settimeout(300)  # 5 minutes for established Datakom connection
            print(f"[OK] Valid Datakom connection from {addr}")
            
        except socket.timeout:
            print(f"[!] Timeout after 10s from {client_ip} (could be slow router/controller)")
            conn.close()
            continue
        except Exception as e:
            print(f"[!] Error reading first packet from {client_ip}: {e}")
            conn.close()
            continue
        
        # Update health status
        update_health("Connected")

        # Process first packet
        conn.sendall(first_data[:8])
        pkt_type = classify_packet(first_data)
        
        if pkt_type == "keepalive":
            keepalive_counter += 1
        elif pkt_type == "telemetry":
            hex_preview = first_data[:16].hex()
            ascii_preview = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in first_data[:40])
            print(f"\n{'='*60}")
            print(f"Packet: {pkt_type.upper()} | Size: {len(first_data)} bytes | From: {addr[0]}")
            print(f"  Hex: {hex_preview}")
            print(f"  ASCII: {ascii_preview}")
            print(f"{'='*60}\n")
            
            path = save_packet(DIR_TELEMETRY, first_data)
            cleanup_old_packets(DIR_TELEMETRY, 20)
            
            decoded = decode_telemetry(first_data)
            print(format_telemetry(decoded))
            
            alerts = decoded.pop("_alerts_internal", {"shutDown": [], "warning": [], "loadDump": []})
            decoded["timestamp"] = datetime.now().isoformat()
            decoded["raw_packet_file"] = os.path.basename(path)
            
            with open(TELEMETRY_JSON, "w", encoding="utf-8") as f:
                json.dump(decoded, f, indent=2, ensure_ascii=False)
            with open(ALERTS_JSON, "w", encoding="utf-8") as f:
                json.dump(alerts, f, indent=2, ensure_ascii=False)
            
            unknown = decode_unknown_offsets(first_data)
            unknown["timestamp"] = datetime.now().isoformat()
            unknown["raw_packet_file"] = os.path.basename(path)
            with open(UNKNOWN_JSON, "w", encoding="utf-8") as f:
                json.dump(unknown, f, indent=2, ensure_ascii=False)
            
            print(f"Packet: {pkt_type.upper()} | Size: {len(first_data)} bytes")

        # Continue reading subsequent packets from this connection
        while True:
            data = conn.recv(4096)
            if not data:
                break
            
            # Filter HTTP requests in main loop
            if data.startswith(b"GET ") or data.startswith(b"POST ") or \
               data.startswith(b"HEAD ") or data.startswith(b"OPTIONS ") or \
               data.startswith(b"\x16\x03"):
                print(f"[http] request ignored from {client_ip}")
                save_packet(DIR_EVENT, data)
                cleanup_old_packets(DIR_EVENT, 10)
                break

            conn.sendall(data[:8])

            pkt_type = classify_packet(data)
            
            if pkt_type == "keepalive":
                keepalive_counter += 1
                if keepalive_counter % 100 == 0:
                    print(f"[keepalive] {keepalive_counter} (waiting for telemetry...)")
                continue
            
            # Show details only for important packets
            hex_preview = data[:16].hex()
            ascii_preview = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data[:40])
            print(f"\n{'='*60}")
            print(f"Packet: {pkt_type.upper()} | Size: {len(data)} bytes | From: {addr[0]}")
            print(f"  Hex: {hex_preview}")
            print(f"  ASCII: {ascii_preview}")
            print(f"{'='*60}\n")

            if pkt_type == "telemetry":
                path = save_packet(DIR_TELEMETRY, data)
                
                # Decode and display telemetry
                decoded = decode_telemetry(data)
                print(format_telemetry(decoded))
                
                # Extract alerts before saving telemetry
                alerts = decoded.pop("_alerts_internal", {"shutDown": [], "warning": [], "loadDump": []})
                
                # Save decoded data to single JSON file
                decoded["timestamp"] = datetime.now().isoformat()
                decoded["raw_packet_file"] = os.path.basename(path)
                with open(TELEMETRY_JSON, "w", encoding="utf-8") as f:
                    json.dump(decoded, f, indent=2, ensure_ascii=False)
                
                # Save alerts to separate JSON file
                with open(ALERTS_JSON, "w", encoding="utf-8") as f:
                    json.dump(alerts, f, indent=2, ensure_ascii=False)
                
                # Decode and save unknown offsets
                unknown = decode_unknown_offsets(data)
                unknown["timestamp"] = datetime.now().isoformat()
                unknown["raw_packet_file"] = os.path.basename(path)
                with open(UNKNOWN_JSON, "w", encoding="utf-8") as f:
                    json.dump(unknown, f, indent=2, ensure_ascii=False)
            elif pkt_type == "event":
                save_packet(DIR_EVENT, data)
                cleanup_old_packets(DIR_EVENT, 10)

            print(f"Packet: {pkt_type.upper()} | Size: {len(data)} bytes")

    except TimeoutError as e:
        print(f"[!] Connection timeout: {e}")
        print(f"[*] Closing connection, waiting for reconnect...")
        update_health("Timeout", {
            "timestamp": datetime.now().isoformat(),
            "message": str(e),
            "code": "TIMEOUT"
        })
        try:
            conn.close()
        except:
            pass
        continue
    except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError) as e:
        print(f"[!] Connection lost: {e}")
        print(f"[*] Waiting for new connection...")
        update_health("Disconnected", {
            "timestamp": datetime.now().isoformat(),
            "message": str(e),
            "code": "CONNECTION_LOST"
        })
        continue
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
        update_health("Stopped")
        break
    except Exception as e:
        print(f"[!] Error: {e}")
        import traceback
        traceback.print_exc()
        print(f"[*] Waiting for new connection...")
        update_health("Error", {
            "timestamp": datetime.now().isoformat(),
            "message": str(e),
            "code": "UNKNOWN_ERROR",
            "stack": traceback.format_exc()
        })
        continue
