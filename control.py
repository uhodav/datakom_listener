"""
Remote control of the Datakom controller: pushbutton simulation via a Modbus "write single register"
request sent over the controller's own telemetry connection.

Frame format (recovered from Rainbow Plus captures in documentations/*.pcapng):
    b"DKV0MBUS" + MBAP(transaction 0x1234, protocol 0, length 6, unit 1) + PDU(06, 0x2011, value)
The controller echoes the same frame back as confirmation.
"""
import json
import socket
import struct
import threading
import time
from datetime import datetime

from config import CONTROL_QUEUE_SECONDS

MBUS_HEADER = b"DKV0MBUS"
CONTROL_REGISTER = 0x2011
TRANSACTION_ID = 0x1234
UNIT_ID = 1
FC_WRITE_REGISTER = 0x06

# Button bitmask written to CONTROL_REGISTER, verified against controller telemetry in the captures
COMMAND_CODES = {
    "stop": 0x01,
    "auto": 0x02,
    "manual": 0x04,
    "test": 0x08,
    "genset": 0x10,   # load transfer to genset
    "mains": 0x20,    # load transfer to mains
}

CONFIRM_TIMEOUT = 10  # seconds to wait for the controller echo
CONTROL_QUEUE_WAIT = 20  # seconds the API request waits for an offline controller before answering "queued"

# All writes to Datakom connections go through this lock so a command frame never interleaves
# with a packet acknowledgement sent by the connection handler thread
send_lock = threading.Lock()


def build_write_frame(value: int) -> bytes:
    return MBUS_HEADER + struct.pack(">HHHBBHH", TRANSACTION_ID, 0, 6, UNIT_ID,
                                     FC_WRITE_REGISTER, CONTROL_REGISTER, value)


def mbus_frame_length(data: bytes):
    """Total length of a DKV0MBUS frame at the start of data, None if the header is incomplete"""
    if len(data) < 14:
        return None
    return 14 + int.from_bytes(data[12:14], "big")


class ControllerLink:
    """Tracks the live controller connection and matches command confirmations"""

    def __init__(self):
        self._lock = threading.Lock()
        self._command_lock = threading.Lock()
        self._conn = None
        self._addr = None
        self._pending = None  # (value, threading.Event, result dict)
        self._queued = None   # (action, value, threading.Event, result dict, expires_at)

    def attach(self, conn, addr):
        with self._lock:
            self._conn, self._addr = conn, addr

    def detach(self, conn):
        with self._lock:
            if self._conn is conn:
                self._conn, self._addr = None, None

    def on_frame(self, frame: bytes):
        """Called by the connection handler for every DKV0MBUS frame received from the controller"""
        with self._lock:
            pending = self._pending
        if frame == MBUS_HEADER:
            # Bare 8-byte header: the controller sends it to every server it is connected to when it
            # receives a command (ours or the Datakom portal's) - a notification, nothing to match
            return
        if len(frame) < 17:
            print(f"[CMD] Short Modbus frame from controller: {frame.hex()}")
            return
        fc = frame[15]
        if fc == FC_WRITE_REGISTER and len(frame) >= 20:
            register, value = struct.unpack(">HH", frame[16:20])
            if pending and register == CONTROL_REGISTER and value == pending[0]:
                print(f"[CMD] Command 0x{value:02X} confirmed by controller")
                pending[2].update(success=True)
                pending[1].set()
                return
            print(f"[CMD] Unexpected confirmation: register 0x{register:04X} value 0x{value:04X}")
        elif fc == FC_WRITE_REGISTER | 0x80:
            print(f"[CMD] Controller rejected command, Modbus exception {frame[16]}")
            if pending:
                pending[2].update(success=False, error=f"Controller rejected command (Modbus exception {frame[16]})")
                pending[1].set()
        else:
            print(f"[CMD] Unexpected Modbus frame from controller: {frame.hex()}")

    def flush_queued(self, conn):
        """Called by the connection handler after each packet: send a command queued while the
        controller was offline. Does not wait for the confirmation (on_frame handles it)."""
        with self._lock:
            queued = self._queued
            if queued is None or self._conn is not conn:
                return
            self._queued = None
            action, value, event, result, expires_at = queued
            if time.time() > expires_at:
                print(f"[CMD] Queued {action.upper()} expired, not sent")
                result.update(success=False, error="Queued command expired before the controller connected")
                event.set()
                return
            self._pending = (value, event, result)
        try:
            with send_lock:
                conn.sendall(build_write_frame(value))
            print(f"[CMD] Sent queued {action.upper()} (0x{value:02X}) to {self._addr}")
        except OSError as e:
            result.update(success=False, error=f"Send failed: {e}")
            event.set()

    def execute(self, action: str) -> dict:
        """Send a command and wait for the controller echo. Commands are serialized.
        While the controller is offline the command is queued (newest wins) for CONTROL_QUEUE_SECONDS."""
        value = COMMAND_CODES.get(action)
        if value is None:
            return {"success": False, "error": f"Unknown action: {action}"}

        with self._command_lock:
            event, result = threading.Event(), {}
            with self._lock:
                conn, addr = self._conn, self._addr
                if conn is None:
                    if self._queued:
                        self._queued[3].update(success=False, error="Replaced by a newer command")
                        self._queued[2].set()
                    expires_at = time.time() + CONTROL_QUEUE_SECONDS
                    self._queued = (action, value, event, result, expires_at)
                    print(f"[CMD] Controller offline, {action.upper()} queued for {CONTROL_QUEUE_SECONDS}s")
                else:
                    self._pending = (value, event, result)
            try:
                if conn is not None:
                    with send_lock:
                        conn.sendall(build_write_frame(value))
                    print(f"[CMD] Sent {action.upper()} (0x{value:02X}) to {addr}")
                    wait = CONFIRM_TIMEOUT
                else:
                    wait = CONTROL_QUEUE_WAIT
                if not event.wait(wait):
                    with self._lock:
                        still_queued = self._queued is not None and self._queued[2] is event
                    if still_queued:
                        return {"success": True, "queued": True, "action": action,
                                "expires_at": datetime.fromtimestamp(expires_at).isoformat()}
                    print(f"[CMD] No confirmation for {action.upper()} within {wait}s")
                    return {"success": False, "error": f"No confirmation from controller within {wait}s"}
                if result.get("success"):
                    return {"success": True, "action": action, "confirmed_at": datetime.now().isoformat()}
                return {"success": False, "error": result.get("error", "Command failed")}
            except OSError as e:
                return {"success": False, "error": f"Send failed: {e}"}
            finally:
                with self._lock:
                    if self._pending is not None and self._pending[1] is event:
                        self._pending = None


link = ControllerLink()


def serve_control(host: str, port: int):
    """Local-only JSON line protocol used by the API process: {"action": "stop"} -> result"""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(5)
    print(f"[+] Control port on {host}:{port}")
    while True:
        client, _ = srv.accept()
        threading.Thread(target=_handle_control_client, args=(client,), daemon=True).start()


def _handle_control_client(client: socket.socket):
    try:
        client.settimeout(5)
        request = json.loads(client.recv(1024).decode("utf-8"))
        client.settimeout(max(CONFIRM_TIMEOUT, CONTROL_QUEUE_WAIT) + 5)
        action = str(request.get("action", "")).lower()
        print(f"[CMD] Request {action.upper()} from {request.get('source', 'unknown')}")
        response = link.execute(action)
    except Exception as e:
        response = {"success": False, "error": f"Bad control request: {e}"}
    try:
        client.sendall((json.dumps(response) + "\n").encode("utf-8"))
    except OSError:
        pass
    finally:
        client.close()
