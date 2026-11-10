"""
Controller outputs and weekly scheduler, read (and the scheduler written) over the controller's own
connection with Modbus requests, the way Rainbow Plus does it (decompiled MainFrm_D500MK2).

Configuration layout (D-500): register = 128 + word of the Rainbow Plus configuration buffer, blocks of
128 words, word 0 = 0xAAAA, word 1 = sum of the bytes of words 2..127 (written as 0, the controller
computes it).
- Block 512..639 ("extra" parameters): passwords 530..532, weekly scheduler 546..559 - two words per
  day Monday..Sunday, bit h = hour h (0..15 in the first word, 16..23 in the second): the hours when
  AUTO mode may run the genset.
- Block 640..767 (I/O): output functions 686..725 = outputs 1..40 (index into output_functions.json).
- Output state: registers 11164..11166 = outputs 1-8 (bits 0-7), 9-24, 25-40. The telemetry packet carries
  the same bits at offsets 112 (outputs 1-8) and 113-116 (9-40, little endian) - verified 10.11.2026:
  registers 0x0040 0x0404 0x4040 = packet 40 04 04 40 40.

Output states are updated from every telemetry packet (update_states_from_packet). Output functions and
the scheduler are read with Modbus requests in a background thread every IO_CONFIG_POLL_SECONDS.
"""
import json
import os
import threading
import time
from datetime import datetime

from control import link

DATA_DIR = "data"
IO_JSON = os.path.join(DATA_DIR, "controller_io.json")
FUNCTIONS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_functions.json")

CONFIG_BASE = 128
BLOCK_WORDS = 128
BLOCK_MARK = 0xAAAA
EXTRA_BLOCK = CONFIG_BASE + 384                 # 512
SCHEDULE_REGISTER = EXTRA_BLOCK + 18 + 16       # 546
SCHEDULE_WORDS = 14
PASSWORDS_REGISTER = EXTRA_BLOCK + 18           # 530..532
IO_BLOCK = CONFIG_BASE + 512                    # 640
OUTPUT_FUNCTION_REGISTER = IO_BLOCK + 46        # 686
OUTPUTS = 40
OUTPUT_STATE_REGISTER = 11164
READ_UNLOCK_REGISTER = 10615
PASSWORD_REGISTER = 8192
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

IO_CONFIG_POLL_SECONDS = 600
PACKET_OUTPUTS_OFFSET = 112  # 5 bytes: outputs 1-8, 9-24 (2 bytes LE), 25-40 (2 bytes LE)

_lock = threading.Lock()          # one poll / scheduler write at a time
_poll_running = threading.Event()
_last_config_poll = 0.0
_functions = None


def output_function_name(index: int) -> str:
    global _functions
    if _functions is None:
        try:
            with open(FUNCTIONS_JSON, encoding="utf-8") as f:
                _functions = sum(json.load(f), [])
        except (OSError, ValueError):
            _functions = []
    return _functions[index] if 0 <= index < len(_functions) else f"Function {index}"


def block_checksum(words: list) -> int:
    return sum((w & 0xFF) + (w >> 8) for w in words[2:BLOCK_WORDS]) & 0xFFFF


def schedule_from_words(words: list) -> dict:
    """14 words -> {"mon": [6, 7, ..., 23], ...}"""
    result = {}
    for d, day in enumerate(DAYS):
        bits = words[2 * d] | (words[2 * d + 1] << 16)
        result[day] = [h for h in range(24) if bits >> h & 1]
    return result


def schedule_to_words(schedule: dict) -> list:
    words = []
    for day in DAYS:
        bits = sum(1 << h for h in schedule[day])
        words += [bits & 0xFFFF, bits >> 16]
    return words


def _load() -> dict:
    try:
        with open(IO_JSON, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(data: dict):
    tmp = IO_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, IO_JSON)


def _read(register: int, count: int) -> list:
    result = link.read_registers(register, count)
    if not result.get("success"):
        raise RuntimeError(f"read {register} x{count}: {result.get('error')}")
    return result["values"]


def _apply_states(data: dict, bits: int, raw, source: str):
    for o in data.get("outputs") or []:
        o["state"] = bool(bits >> (o["output"] - 1) & 1)
    data["output_state_raw"] = raw
    data["output_state_source"] = source
    data["timestamp"] = datetime.now().isoformat()


def update_states_from_packet(packet: bytes):
    """Output states from a telemetry packet (bytes 112-116), saved with the last read functions."""
    if len(packet) < PACKET_OUTPUTS_OFFSET + 5:
        return
    raw = packet[PACKET_OUTPUTS_OFFSET:PACKET_OUTPUTS_OFFSET + 5]
    bits = raw[0] | int.from_bytes(raw[1:3], "little") << 8 | int.from_bytes(raw[3:5], "little") << 24
    # Called from the connection handler thread: never wait for _lock - a poll or a scheduler write holding
    # it waits for controller answers that only this thread delivers. Busy -> skip (the poll saves states).
    if not _lock.acquire(blocking=False):
        return
    try:
        data = _load()
        if not data.get("outputs"):
            return  # functions not read yet: the first poll writes the states too
        _apply_states(data, bits, raw.hex(" "), "telemetry")
        _save(data)
    finally:
        _lock.release()


def poll(force_config: bool = False) -> dict:
    """Read output functions, the scheduler and output states (Modbus) into data/controller_io.json."""
    global _last_config_poll
    with _lock:
        data = _load()
        states = _read(OUTPUT_STATE_REGISTER, 3)
        bits = (states[0] & 0xFF) | (states[1] << 8) | (states[2] << 24)
        functions = _read(OUTPUT_FUNCTION_REGISTER, OUTPUTS)
        data["outputs"] = [
            {"output": n + 1, "function_index": f, "function": output_function_name(f)}
            for n, f in enumerate(functions)
        ]
        data["schedule"] = schedule_from_words(_read(SCHEDULE_REGISTER, SCHEDULE_WORDS))
        data["config_timestamp"] = datetime.now().isoformat()
        _apply_states(data, bits, states, "modbus")
        data.pop("error", None)
        _save(data)
        _last_config_poll = time.time()
        return data


def poll_after_packet():
    """Called by the connection handler after each telemetry packet: read functions and the scheduler
    in the background when due (the handler thread must keep reading - it delivers the answers)."""
    if _poll_running.is_set() or time.time() - _last_config_poll < IO_CONFIG_POLL_SECONDS:
        return

    def run():
        try:
            poll()
        except Exception as e:
            print(f"[IO] Poll failed: {e}")
            global _last_config_poll
            _last_config_poll = time.time() - IO_CONFIG_POLL_SECONDS + 60  # retry in a minute
            data = _load()
            data["error"] = str(e)
            data["error_at"] = datetime.now().isoformat()
            try:
                _save(data)
            except OSError:
                pass
        finally:
            _poll_running.clear()

    _poll_running.set()
    threading.Thread(target=run, daemon=True).start()


def _unlock_write(passwords: list):
    """Rainbow Plus order: read-unlock code (10615) -> 8192, then the configuration password -> 8192."""
    for value in (_read(READ_UNLOCK_REGISTER, 1)[0], passwords[1]):
        result = link.execute("raw", PASSWORD_REGISTER, value)
        if not result.get("success"):
            raise RuntimeError(f"unlock: {result.get('error')}")
        time.sleep(0.1)


def set_schedule(changes: dict) -> dict:
    """changes = {"mon": [6, ..., 23], ...} (any subset of days). Reads the whole block 512..639,
    checks it, changes the scheduler words, writes the block back (checksum 0 as Rainbow Plus does)
    and reads it back to verify."""
    try:
        for day, hours in changes.items():
            if day not in DAYS or not all(isinstance(h, int) and 0 <= h <= 23 for h in hours):
                return {"success": False, "error": f"Bad schedule for {day}: hours must be 0..23"}
        with _lock:
            block = _read(EXTRA_BLOCK, 64) + _read(EXTRA_BLOCK + 64, 64)
            if block[0] != BLOCK_MARK or block[1] != block_checksum(block):
                return {"success": False, "error": "Configuration block check failed, nothing written"}
            offset = SCHEDULE_REGISTER - EXTRA_BLOCK
            current = schedule_from_words(block[offset:offset + SCHEDULE_WORDS])
            wanted = {**current, **{d: sorted(set(h)) for d, h in changes.items()}}
            if wanted == current:
                return {"success": True, "changed": False, "schedule": current}
            new_block = list(block)
            new_block[offset:offset + SCHEDULE_WORDS] = schedule_to_words(wanted)
            new_block[1] = 0
            passwords = block[PASSWORDS_REGISTER - EXTRA_BLOCK:PASSWORDS_REGISTER - EXTRA_BLOCK + 3]
            _unlock_write(passwords)
            for part in (0, 64):
                result = link.write_registers(EXTRA_BLOCK + part, new_block[part:part + 64])
                if not result.get("success"):
                    raise RuntimeError(f"write {EXTRA_BLOCK + part}: {result.get('error')}")
            time.sleep(0.5)
            check = _read(EXTRA_BLOCK, 64) + _read(EXTRA_BLOCK + 64, 64)
            written = schedule_from_words(check[offset:offset + SCHEDULE_WORDS])
            others_kept = all(check[i] == block[i] for i in range(2, BLOCK_WORDS)
                              if not offset <= i < offset + SCHEDULE_WORDS)
            print(f"[IO] Scheduler written: {written}, checksum 0x{check[1]:04X} "
                  f"(expected 0x{block_checksum(new_block):04X}), other words kept: {others_kept}")
            data = _load()
            data["schedule"] = written
            data["config_timestamp"] = datetime.now().isoformat()
            _save(data)
            ok = written == wanted and others_kept
            return {"success": ok, "changed": True, "schedule": written,
                    "checksum_ok": check[1] == block_checksum(check),
                    **({} if ok else {"error": "Read-back differs from what was written"})}
    except Exception as e:
        return {"success": False, "error": str(e)}
