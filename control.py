"""
Remote control of the Datakom controller: pushbutton simulation via a Modbus "write single register"
request sent over the controller's own telemetry connection (also run, service counter reset and
user outputs, see REGISTER_COMMANDS / resolve_command).

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
FC_READ_REGISTERS = 0x03
FC_WRITE_REGISTERS = 0x10
MAX_READ_COUNT = 123  # Modbus limit per request (Rainbow Plus reads 64-word blocks)

# Button bitmask written to CONTROL_REGISTER, verified against controller telemetry in the captures
COMMAND_CODES = {
    "stop": 0x01,
    "auto": 0x02,
    "manual": 0x04,
    "test": 0x08,
    "genset": 0x10,   # load transfer to genset
    "mains": 0x20,    # load transfer to mains
}

# Rainbow Plus (D-500 / D-500 MK2) writes front panel buttons to register 8193 and other commands to
# their own registers (decompiled MainFrm_D500MK2: SendSimulateButton, ResetDevCounters, SetUserOutputs)
PANEL_BUTTON_REGISTER = 8193   # STOP=1, MAN=2, AUTO=4, TEST=8, RUN=18 (MAN+RUN bits), GCB=32, MCB=64
COUNTER_RESET_REGISTER = 8196  # bitmask: runs 1, cranks 2, service 1/2/3 = 8/16/32, kWh 64, all 511
USER_OUTPUT_REGISTER = 8201    # output number 1..16, | 0x8000 switches it off
USER_OUTPUTS = 16
REGISTER_COMMANDS = {
    "run": (PANEL_BUTTON_REGISTER, 18),
    "service1_reset": (COUNTER_RESET_REGISTER, 8),
}


def resolve_command(request: dict):
    """(action, register, value) for a control request, or an error string.
    "output" needs "output" (1..16) and "state" ("on"/"off"); "raw" needs "register" and "value"."""
    action = str(request.get("action", "")).lower()
    if action in COMMAND_CODES:
        return action, CONTROL_REGISTER, COMMAND_CODES[action]
    if action in REGISTER_COMMANDS:
        return (action, *REGISTER_COMMANDS[action])
    try:
        if action == "output":
            output = int(request.get("output"))
            state = str(request.get("state", "")).lower()
            if not 1 <= output <= USER_OUTPUTS or state not in ("on", "off"):
                return f"output must be 1..{USER_OUTPUTS} and state on/off"
            return action, USER_OUTPUT_REGISTER, output | (0x8000 if state == "off" else 0)
        if action == "raw":
            register, value = int(request.get("register", CONTROL_REGISTER)), int(request["value"])
            if 0 <= register <= 0xFFFF and 0 <= value <= 0xFFFF:
                return action, register, value
            return "register and value must be 0..65535"
    except (TypeError, ValueError, KeyError) as e:
        return f"Bad {action} request: {e}"
    return f"Unknown action: {action}"

CONFIRM_TIMEOUT = 10  # seconds to wait for the controller echo
CONTROL_QUEUE_WAIT = 20  # seconds the API request waits for an offline controller before answering "queued"

# All writes to Datakom connections go through this lock so a command frame never interleaves
# with a packet acknowledgement sent by the connection handler thread
send_lock = threading.Lock()


def build_write_frame(value: int, register: int = CONTROL_REGISTER) -> bytes:
    return MBUS_HEADER + struct.pack(">HHHBBHH", TRANSACTION_ID, 0, 6, UNIT_ID,
                                     FC_WRITE_REGISTER, register, value)


def build_read_frame(register: int, count: int) -> bytes:
    return MBUS_HEADER + struct.pack(">HHHBBHH", TRANSACTION_ID, 0, 6, UNIT_ID,
                                     FC_READ_REGISTERS, register, count)


def build_write_multi_frame(register: int, values: list) -> bytes:
    n = len(values)
    return MBUS_HEADER + struct.pack(f">HHHBBHHB{n}H", TRANSACTION_ID, 0, 7 + 2 * n, UNIT_ID,
                                     FC_WRITE_REGISTERS, register, n, 2 * n, *values)


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
        self._pending = None  # (register, value, threading.Event, result dict)
        self._queued = None   # (action, register, value, threading.Event, result dict, expires_at)
        self._pending_tx = None  # read / write-multiple: (function code, threading.Event, result dict)

    def attach(self, conn, addr):
        with self._lock:
            self._conn, self._addr = conn, addr

    def ensure_attached(self, conn, addr) -> bool:
        """Called for every packet: the connection that is actually delivering data is the live one.
        The controller can hold an older connection while a newer one drops ("Connection reset by peer");
        without this the link stays detached and commands wait in the queue forever.
        Returns True when the link was switched to this connection."""
        with self._lock:
            if self._conn is conn:
                return False
            self._conn, self._addr = conn, addr
        print(f"[CMD] Live controller connection {addr} re-attached for commands")
        return True

    def detach(self, conn):
        with self._lock:
            if self._conn is conn:
                self._conn, self._addr = None, None

    def on_frame(self, frame: bytes):
        """Called by the connection handler for every DKV0MBUS frame received from the controller"""
        with self._lock:
            pending = self._pending
            pending_tx = self._pending_tx
        if frame == MBUS_HEADER:
            # Bare 8-byte header: the controller sends it to every server it is connected to when it
            # receives a command (ours or the Datakom portal's) - a notification, nothing to match
            return
        if len(frame) < 17:
            print(f"[CMD] Short Modbus frame from controller: {frame.hex()}")
            return
        fc = frame[15]
        if pending_tx and fc in (pending_tx[0], pending_tx[0] | 0x80):
            if fc & 0x80:
                pending_tx[2].update(success=False, error=f"Controller rejected request (Modbus exception {frame[16]})")
            elif fc == FC_READ_REGISTERS:
                count = frame[16] // 2
                pending_tx[2].update(success=True, values=list(struct.unpack_from(f">{count}H", frame, 17)))
            else:
                pending_tx[2].update(success=True, register=struct.unpack_from(">H", frame, 16)[0],
                                     count=struct.unpack_from(">H", frame, 18)[0])
            print(f"[CMD] Modbus function {fc & 0x7F} answered: {pending_tx[2]}")
            pending_tx[1].set()
            return
        if fc == FC_WRITE_REGISTER and len(frame) >= 20:
            register, value = struct.unpack(">HH", frame[16:20])
            if pending and register == pending[0] and value == pending[1]:
                print(f"[CMD] Command 0x{value:02X} (register 0x{register:04X}) confirmed by controller")
                pending[3].update(success=True)
                pending[2].set()
                return
            print(f"[CMD] Unexpected confirmation: register 0x{register:04X} value 0x{value:04X}")
        elif fc == FC_WRITE_REGISTER | 0x80:
            print(f"[CMD] Controller rejected command, Modbus exception {frame[16]}")
            if pending:
                pending[3].update(success=False, error=f"Controller rejected command (Modbus exception {frame[16]})")
                pending[2].set()
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
            action, register, value, event, result, expires_at = queued
            if time.time() > expires_at:
                print(f"[CMD] Queued {action.upper()} expired, not sent")
                result.update(success=False, error="Queued command expired before the controller connected")
                event.set()
                return
            self._pending = (register, value, event, result)
        try:
            with send_lock:
                conn.sendall(build_write_frame(value, register))
            print(f"[CMD] Sent queued {action.upper()} (0x{value:02X}) to {self._addr}")
        except OSError as e:
            result.update(success=False, error=f"Send failed: {e}")
            event.set()

    def execute(self, action: str, register: int = None, value: int = None) -> dict:
        """Send a command and wait for the controller echo. Commands are serialized.
        While the controller is offline the command is queued (newest wins) for CONTROL_QUEUE_SECONDS.
        register/value default to the code of action (see resolve_command)."""
        if value is None:
            resolved = resolve_command({"action": action})
            if isinstance(resolved, str):
                return {"success": False, "error": resolved}
            action, register, value = resolved

        with self._command_lock:
            event, result = threading.Event(), {}
            with self._lock:
                conn, addr = self._conn, self._addr
                if conn is None:
                    if self._queued:
                        self._queued[4].update(success=False, error="Replaced by a newer command")
                        self._queued[3].set()
                    expires_at = time.time() + CONTROL_QUEUE_SECONDS
                    self._queued = (action, register, value, event, result, expires_at)
                    print(f"[CMD] Controller offline, {action.upper()} queued for {CONTROL_QUEUE_SECONDS}s")
                else:
                    self._pending = (register, value, event, result)
            try:
                if conn is not None:
                    with send_lock:
                        conn.sendall(build_write_frame(value, register))
                    print(f"[CMD] Sent {action.upper()} (0x{value:02X} to register 0x{register:04X}) to {addr}")
                    wait = CONFIRM_TIMEOUT
                else:
                    wait = CONTROL_QUEUE_WAIT
                if not event.wait(wait):
                    with self._lock:
                        still_queued = self._queued is not None and self._queued[3] is event
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
                    if self._pending is not None and self._pending[2] is event:
                        self._pending = None

    def transact(self, fc: int, frame: bytes, timeout: float = CONFIRM_TIMEOUT) -> dict:
        """Send a read (03) or write-multiple (16) request and wait for the answer. Not queued:
        the controller must be connected. Serialized with the pushbutton commands."""
        with self._command_lock:
            with self._lock:
                conn, addr = self._conn, self._addr
                if conn is None:
                    return {"success": False, "error": "Controller is not connected"}
                event, result = threading.Event(), {}
                self._pending_tx = (fc, event, result)
            try:
                with send_lock:
                    conn.sendall(frame)
                print(f"[CMD] Sent Modbus function {fc} request {frame[8:].hex()} to {addr}")
                if not event.wait(timeout):
                    return {"success": False, "error": f"No answer from controller within {timeout}s"}
                return result
            except OSError as e:
                return {"success": False, "error": f"Send failed: {e}"}
            finally:
                with self._lock:
                    if self._pending_tx is not None and self._pending_tx[1] is event:
                        self._pending_tx = None

    def read_registers(self, register: int, count: int) -> dict:
        if not (0 <= register <= 0xFFFF and 1 <= count <= MAX_READ_COUNT):
            return {"success": False, "error": f"register 0..65535, count 1..{MAX_READ_COUNT}"}
        result = self.transact(FC_READ_REGISTERS, build_read_frame(register, count))
        if result.get("success"):
            result = {**result, "register": register}
        return result

    def write_registers(self, register: int, values: list) -> dict:
        if not (0 <= register <= 0xFFFF and 1 <= len(values) <= MAX_READ_COUNT - 2
                and all(0 <= v <= 0xFFFF for v in values)):
            return {"success": False, "error": "register 0..65535, 1..121 values 0..65535"}
        return self.transact(FC_WRITE_REGISTERS, build_write_multi_frame(register, values))


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
        request = json.loads(client.recv(16384).decode("utf-8"))
        client.settimeout(max(CONFIRM_TIMEOUT, CONTROL_QUEUE_WAIT) + 5)
        action = str(request.get("action", "")).lower()
        print(f"[CMD] Request {action.upper()} from {request.get('source', 'unknown')}")
        # Local control port only (not allowed by the API): read / write any registers, for testing
        if action in ("schedule_set", "io_refresh"):
            import controller_io  # imports control: loaded on first use
            if action == "schedule_set":
                response = controller_io.set_schedule(request.get("schedule") or {})
            else:
                response = {"success": True, **controller_io.poll(force_config=True)}
        elif action == "read":
            response = link.read_registers(int(request["register"]), int(request.get("count", 1)))
        elif action == "write_multi":
            response = link.write_registers(int(request["register"]), [int(v) for v in request["values"]])
        else:
            resolved = resolve_command(request)
            if isinstance(resolved, str):
                response = {"success": False, "error": resolved}
            else:
                response = link.execute(*resolved)
    except Exception as e:
        response = {"success": False, "error": f"Bad control request: {e}"}
    try:
        client.sendall((json.dumps(response) + "\n").encode("utf-8"))
    except OSError:
        pass
    finally:
        client.close()
