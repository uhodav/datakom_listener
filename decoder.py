"""
Decoder for Datakom D500 MK3 telemetry packets
"""

from datetime import datetime
from datakom_constants import (
    MODE_NAMES, STATE_NAMES,
    get_alert_category_by_index, get_alarm_index_by_message
)


# Fixed-layout fields: key -> (offset, size in bytes, divisor, signed, unit).
# Offsets, sizes, multipliers and signedness follow structure/DK0ED500.json
# (MulIdx 0 -> x1, 6 -> /10, 9 -> /100, 10 -> /1000). Keys are referenced by param_mapping.py.
TEMPLATE_FIELDS = {
    # Information
    "modbus_addr": (18, 1, 1, False, ""),
    "modbus_port": (19, 2, 1, False, ""),
    # Mains
    "mains_L1_V": (125, 4, 10, True, "V"),
    "mains_L2_V": (129, 4, 10, True, "V"),
    "mains_L3_V": (133, 4, 10, True, "V"),
    "mains_I1_A": (137, 4, 10, True, "A"),
    "mains_I2_A": (141, 4, 10, True, "A"),
    "mains_I3_A": (145, 4, 10, True, "A"),
    "mains_L1_L2_V": (149, 4, 10, True, "V"),
    "mains_L2_L3_V": (153, 4, 10, True, "V"),
    "mains_L3_L1_V": (157, 4, 10, True, "V"),
    "mains_P_total_kW": (161, 4, 10, True, "kW"),
    "mains_Q_total_kVAr": (165, 4, 10, True, "kVAr"),
    "mains_S_total_kVA": (169, 4, 10, True, "kVA"),
    "mains_power_factor": (173, 2, 1000, True, ""),
    "mains_freq_Hz": (175, 2, 100, False, "Hz"),
    "mains_in": (177, 4, 10, True, "A"),
    # Genset
    "genset_L1_V": (181, 4, 10, True, "V"),
    "genset_L2_V": (185, 4, 10, True, "V"),
    "genset_L3_V": (189, 4, 10, True, "V"),
    "genset_I1_A": (193, 4, 10, True, "A"),
    "genset_I2_A": (197, 4, 10, True, "A"),
    "genset_I3_A": (201, 4, 10, True, "A"),
    "genset_L1_L2_V": (205, 4, 10, True, "V"),
    "genset_L2_L3_V": (209, 4, 10, True, "V"),
    "genset_L3_L1_V": (213, 4, 10, True, "V"),
    "genset_P_total_kW": (217, 4, 10, True, "kW"),
    "genset_Q_total_kVAr": (221, 4, 10, True, "kVAr"),
    "genset_S_total_kVA": (225, 4, 10, True, "kVA"),
    "genset_power_factor": (229, 2, 1000, True, ""),
    "genset_freq_Hz": (231, 2, 100, False, "Hz"),
    "genset_in": (233, 4, 10, True, "A"),
    # Engine
    "engine_rpm": (237, 2, 1, False, "RPM"),
    "battery_voltage_Vdc": (239, 2, 100, True, "Vdc"),
    "charge_voltage": (241, 2, 100, True, "Vdc"),
    "oil_pressure_bar": (243, 2, 10, False, "Bar"),
    "coolant_temp_C": (245, 2, 10, True, "'C"),
    "fuel_level_percent": (247, 2, 10, True, "%"),
    "oil_temp": (249, 2, 10, True, "'C"),
    "canopy_temp": (251, 2, 10, True, "'C"),
    # Counters
    "genset_starts_count": (503, 4, 1, True, ""),
    "genset_cranks_count": (507, 4, 1, True, ""),
    "engine_run_hours_total": (511, 4, 100, True, "hour"),
    "hours_to_service_1": (515, 4, 100, True, "hour"),
    "days_to_service_1": (519, 4, 100, True, "day"),
    "hours_to_service_2": (523, 4, 100, True, "hour"),
    "days_to_service_2": (527, 4, 100, True, "day"),
    "hours_to_service_3": (531, 4, 100, True, "hour"),
    "days_to_service_3": (535, 4, 100, True, "day"),
    "total_kWh": (539, 4, 10, True, "kWh"),
    "reactive_energy_inductive": (543, 4, 10, True, "kVArh"),
    "reactive_energy_capacitive": (547, 4, 10, True, "kVArh"),
    "engine_power_rate_percent": (553, 2, 1, True, "kW"),
    "battery_voltage_2_Vdc": (555, 2, 100, True, "Vdc"),
    "mains_total_kWh": (561, 4, 10, True, "kWh"),
    "mains_total_kVArh_ind": (565, 4, 10, True, "kVArh"),
    "mains_total_kVArh_cap": (569, 4, 10, True, "kVArh"),
    "mains_total_export_kWh": (573, 4, 10, True, "kWh"),
    "fuel_consumption_flowm": (577, 4, 1000, True, "lt."),
    "satellites": (589, 1, 1, False, ""),
    "mac_reset": (590, 2, 1, False, ""),
    "fuel_consumption_ecu": (598, 4, 1, False, "lt."),
    "min_battery_voltage": (602, 2, 100, True, "Vdc"),
    "battery_group_voltage": (604, 2, 10, True, "Vdc"),
    "battery_group_current": (606, 2, 10, True, "A"),
    "discharge_current_counter": (608, 4, 10, False, "Ah"),
    "fuel_rate_flowm": (612, 2, 10, False, "lt./h"),
    "fuel_rate_ecu": (614, 2, 10, False, "lt./h"),
    "alternator_voltage": (616, 2, 10, True, "Vdc"),
    "load_battery_voltage": (618, 2, 10, True, "Vdc"),
    "dc_actual_current": (620, 2, 10, True, "A"),
    "dc_battery_temp": (622, 2, 10, True, "'C"),
    "dc_charge_state": (624, 1, 1, False, ""),
}

# Analog sender slots in packet order; keys are referenced by param_mapping.py
SENDER_KEYS = ["sender_oil_pressure", "sender_engine_temp", "sender_fuel_level_1", "sender_fuel_level_2"]
# Sender type byte -> unit (seen: 1 oil pressure, 3 coolant temp, 5 fuel level)
SENDER_UNITS = {1: "Bar", 3: "'C", 5: "%"}

ALARM_HEAD = 407
ALARM_SIZE = 96
ALARM_SECTION_ORDER = ["shutDown", "loadDump", "warning"]


# Raw values meaning "sensor not fitted / not available"
NOT_AVAILABLE = {
    (1, False): (0xFF,), (2, False): (0xFFFF,), (4, False): (0xFFFFFFFF,),
    (2, True): (0x7FFF, -0x8000), (4, True): (0x7FFFFFFF, -0x80000000),
}


def read_number(data: bytes, offset: int, size: int, divisor: int = 1, signed: bool = False):
    """Read a little-endian integer field; None if the field is outside the packet or holds a
    'not available' marker, otherwise the value scaled by divisor"""
    if len(data) < offset + size:
        return None
    raw = int.from_bytes(data[offset:offset + size], "little", signed=signed)
    if raw in NOT_AVAILABLE.get((size, signed), ()):
        return None
    if divisor == 1:
        return raw
    return round(raw / divisor, len(str(divisor)) - 1)


SERVICE_COUNTER_KEYS = [
    "hours_to_service_1", "days_to_service_1",
    "hours_to_service_2", "days_to_service_2",
    "hours_to_service_3", "days_to_service_3",
]

# Enum texts as shown by the official Datakom portal (only observed values are known)
CONNECTION_TYPES = {0: "LAN"}
INFORMATION_FLAGS = {0: "Fuel:Burn,Fuel:lt,Position:GPS"}


def format_version(raw: int) -> str:
    """Version word as the portal shows it: hex digits with a dot before the last one (0x0243 -> 24.3)"""
    digits = f"{raw:x}".rjust(2, "0")
    return f"{digits[:-1]}.{digits[-1]}"


def read_text(data: bytes, offset: int, size: int):
    """Read an ASCII field padded with '-' or NUL; None if empty"""
    text = data[offset:offset + size].decode("ascii", errors="ignore").strip("\x00- ")
    return text or None


def format_ip(data: bytes, offset: int):
    if len(data) < offset + 4:
        return "N/A"
    return ".".join(str(b) for b in data[offset:offset + 4])


def decode_device_datetime(raw: bytes) -> str:
    """Decode packed date/time: bits 0-4 sec/2, 5-10 min, 11-15 hour, 16-20 day, 21-24 month, 25-31 year-2000"""
    if len(raw) < 4:
        return "N/A"
    v = int.from_bytes(raw, "little")
    try:
        dt = datetime(2000 + (v >> 25), (v >> 21) & 0xF, (v >> 16) & 0x1F,
                      (v >> 11) & 0x1F, (v >> 5) & 0x3F, (v & 0x1F) * 2)
    except ValueError:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def make_measurement(value, unit=""):
    """Create measurement object with value and unit"""
    if isinstance(value, tuple) and len(value) == 4:
        val, data, min_len, empty_value = value
        if len(data) < min_len:
            return {"value": empty_value, "unit": unit}
        value = val
    return {
        "value": value,
        "unit": unit
    }


def decode_telemetry(data: bytes) -> dict:
    """Decode telemetry packet from Datakom D500 MK3 controller"""
    
    if len(data) < 300:
        return {"error": f"Packet too short: {len(data)} bytes"}
    
    result = {}
    
    # Harmonic levels (10386–10402)
    for i in range(3, 32):
        offset = 10386 + (i - 3) * 2
        if len(data) > offset + 2:
            result[f"harmonic_{i:02}_level"] = make_measurement(round(int.from_bytes(data[offset:offset+2], "little") / 100, 2), "%")

    # Scopemeter data (10404–10503)
    for i in range(100):
        offset = 10404 + i * 2
        if len(data) > offset + 2:
            result[f"scopemeter_point_{i+1}"] = make_measurement(int.from_bytes(data[offset:offset+2], "little"), "")

    # Shutdown/LoadDump/Warning alarm bits (10504–10551)
    for alarm_type, base in zip(["shutdown_bits", "loaddump_bits", "warning_bits"], [10504, 10520, 10536]):
        bits = []
        for i in range(16):
            offset = base + i * 2
            if len(data) > offset + 2:
                bits.append(int.from_bytes(data[offset:offset+2], "little"))
        result[alarm_type] = bits

    # GPS altitude (10598)
    result["gps_altitude"] = make_measurement((int.from_bytes(data[10598:10602], "little"), data, 10601, "N/A"), "m")

    # Multi-genset fields (11175–11378)
    multi_fields = {
        "multi_genset_total_active_power": (11175, "kW"),
        "multi_genset_total_reactive_power": (11177, "kVAr"),
        "multi_genset_avg_active_power_load_percent": (11374, "%"),
        "multi_genset_avg_reactive_power_load_percent": (11375, "%"),
        "multi_genset_avg_power_factor": (11376, ""),
        "multi_genset_speed_correction_percent": (11377, "%"),
        "multi_genset_voltage_correction_percent": (11378, "%")
    }
    for key, (offset, unit) in multi_fields.items():
        result[key] = make_measurement((int.from_bytes(data[offset:offset+2], "little"), data, offset+3, "N/A"), unit)

    # Ethernet MAC address (11684–11686)
    result["ethernet_mac"] = make_measurement((data[11684:11687].hex().upper(), data, 11687, "N/A"), "")

    # Controller Unique ID (11687–11692)
    result["controller_unique_id"] = make_measurement((data[11687:11693].hex().upper(), data, 11693, "N/A"), "")

    # Modem IMEI (11693–11700)
    result["modem_imei"] = make_measurement((data[11693:11701].hex().upper(), data, 11701, "N/A"), "")

    # Battery charge current (11173, 11174)
    result["battery_charge_current_1"] = make_measurement((int.from_bytes(data[11173:11175], "little"), data, 11176, "N/A"), "A")
    result["battery_charge_current_2"] = make_measurement((int.from_bytes(data[11175:11177], "little"), data, 11178, "N/A"), "A")

    # Minimum battery voltage (11172)
    result["min_battery_voltage"] = make_measurement((round(int.from_bytes(data[11172:11174], "little") / 100, 2), data, 11175, "N/A"), "V")

    # Flowmeter (11680)
    result["flowmeter"] = make_measurement((round(int.from_bytes(data[11680:11682], "little") / 10, 1), data, 11683, "N/A"), "lt.")

    # Selected channel for harmonic/scopemeter (10403)
    result["selected_channel_harmonic_scopemeter"] = make_measurement((int.from_bytes(data[10403:10405], "little"), data, 10406, "N/A"), "")

    # Magnetic pickup input (10375)
    result["magnetic_pickup_input_rpm"] = make_measurement((int.from_bytes(data[10375:10377], "little"), data, 10378, "N/A"), "RPM")

    # Engine operation timer (10606)
    result["engine_operation_timer"] = make_measurement((int.from_bytes(data[10606:10608], "little"), data, 10609, "N/A"), "s")

    # GOV/AVR control output (10607, 10608)
    result["gov_control_output_percent"] = make_measurement((int.from_bytes(data[10607:10609], "little"), data, 10611, "N/A"), "%")
    result["avr_control_output_percent"] = make_measurement((int.from_bytes(data[10609:10611], "little"), data, 10611, "N/A"), "%")

    # Device hardware/software version (10610, 10611)
    result["device_hw_version"] = make_measurement((int.from_bytes(data[10610:10612], "little"), data, 10613, "N/A"), "")
    result["device_sw_version"] = make_measurement((int.from_bytes(data[10612:10614], "little"), data, 10615, "N/A"), "")

    # Service counters (10622–10644)
    for i, (offset, key, unit, scale) in enumerate([
        (10622, "engine_hours_run", "hour", 100),
        (10624, "engine_hours_since_last_service", "hour", 100),
        (10626, "engine_days_since_last_service", "day", 100),
        (10628, "genset_total_active_energy", "kWh", 10),
        (10630, "genset_total_inductive_reactive_energy", "kVArh-ind", 10),
        (10632, "genset_total_capacitive_reactive_energy", "kVArh-cap", 10),
        (10634, "remaining_engine_hours_to_service_1", "hour", 100),
        (10636, "remaining_engine_days_to_service_1", "day", 100),
        (10638, "remaining_engine_hours_to_service_2", "hour", 100),
        (10640, "remaining_engine_days_to_service_2", "day", 100),
        (10642, "remaining_engine_hours_to_service_3", "hour", 100),
        (10644, "remaining_engine_days_to_service_3", "day", 100)
    ]):
        if len(data) > offset + 4:
            raw_value = int.from_bytes(data[offset:offset+4], "little")
            # Проверка на пустые значения
            if raw_value in (0xFFFFFFFF, 0xFFFFFFFE, 4294967295, 4294967294):
                value = None
            else:
                value = round(raw_value / scale, 2)
                # Если значение float и очень большое (например, >= 42949651), считаем пустым
                if isinstance(value, float) and value >= 42949651:
                    value = None
            result[key] = make_measurement(value, unit)

    # GPRS IP address (10646)
    result["gprs_ip"] = make_measurement((".".join(str(b) for b in data[10646:10650]), data, 10651, "N/A"), "")

    # Extension digital input/output status (11167–11168, 11164–11166)
    result["extension_digital_input_status"] = make_measurement((data[11167:11169].hex().upper(), data, 11170, "N/A"), "")
    result["extension_digital_output_status"] = make_measurement((data[11164:11167].hex().upper(), data, 11168, "N/A"), "")

    # Function flags (11555)
    result["function_flags"] = make_measurement((data[11555:11559].hex().upper(), data, 11560, "N/A"), "")
    
    # Packet header
    result["header"] = make_measurement(data[0:8].decode("ascii", errors="ignore"))

    # Protocol version / packet type (offset 8-15)
    result["protocol_info"] = make_measurement(data[8:16].hex())

    # Fixed-layout fields from the Rainbow Plus template structure/DK0ED500.json
    # (BusAdr = offset = API param id, size = BusCnt + 1, little-endian)
    for key, (offset, size, divisor, signed, unit) in TEMPLATE_FIELDS.items():
        result[key] = make_measurement(read_number(data, offset, size, divisor, signed), unit)

    # Service counters: the official Datakom portal shows negative values as N/A (service not set)
    for key in SERVICE_COUNTER_KEYS:
        value = result[key]["value"]
        if isinstance(value, (int, float)) and value < 0:
            result[key]["value"] = None

    # Device info, formatted like the official Datakom portal
    if len(data) >= 15:
        # Device type (offset 9-10) as hex: 0xD502 -> "d502"
        result["device_type"] = make_measurement(f"{int.from_bytes(data[9:11], 'little'):x}")
        # Versions (offset 11-12, 13-14): hex digits with a dot before the last one, 0x0243 -> "24.3"
        result["sw_version"] = make_measurement(format_version(int.from_bytes(data[11:13], "little")))
        result["hw_version"] = make_measurement(format_version(int.from_bytes(data[13:15], "little")))
    connection = data[8] if len(data) > 8 else None
    result["connection"] = make_measurement(CONNECTION_TYPES.get(connection, connection), "")
    information = read_number(data, 581, 2, 1, False)
    result["information"] = make_measurement(INFORMATION_FLAGS.get(information, information), "")

    # UniqueID (offset 21-32, hex string)
    result["unique_id"] = make_measurement(data[21:33].hex().upper())

    # IP addresses (4 bytes each)
    result["wan_ip"] = make_measurement(format_ip(data, 33), "")
    result["lan_ip"] = make_measurement(format_ip(data, 37))
    result["gsm_ip"] = make_measurement(format_ip(data, 41), "")
    # wan_ip_2 (offset 598-601) overlaps Fuel Consump(ECU) in the template; kept for compatibility
    result["wan_ip_2"] = make_measurement(format_ip(data, 598), "")

    # GPS coordinates (offset 45-52, signed 4 bytes each, scaled by 1000000)
    result["latitude"] = make_measurement(read_number(data, 45, 4, 1_000_000, True), "")
    result["longitude"] = make_measurement(read_number(data, 49, 4, 1_000_000, True), "")

    # Text fields padded with '-' (offset 57-77 site id, 78-98 engine serial)
    result["site_id"] = make_measurement(read_text(data, 57, 21), "")
    result["engine_serial"] = make_measurement(read_text(data, 78, 21), "")
    result["generator_name"] = make_measurement(read_text(data, 57, 21))

    # Controller date/time (offset 99-102): DOS-style packed little-endian 32-bit value,
    # year counted from 2000. Controller clock, not the server's.
    result["device_date"] = make_measurement(decode_device_datetime(data[99:103]), "")

    # Mode (offset 103)
    mode_code = data[103]
    result["mode"] = make_measurement(mode_code)
    result["mode_name"] = make_measurement(MODE_NAMES.get(mode_code, f"Unknown ({mode_code})"))

    # State (offset 105)
    state_code = data[105]
    result["state"] = make_measurement(state_code)
    result["state_name"] = make_measurement(STATE_NAMES.get(state_code, f"Unknown ({state_code})"))

    # MAC Address (offset 592-597)
    result["mac_address"] = make_measurement((data[592:598].hex().upper(), data, 598, "N/A"), "")

    # Panel LED states (offset 112-119): 2 bits per LED - 00 off, 01 on, 10 quick flash, 11 slow flash
    result["panel_leds"] = make_measurement((data[112:120].hex().upper(), data, 120, "N/A"), "")
    # Same LED block in the Datakom portal layout (offset 117-124, bit index as in portal DK_bit_obtain):
    # 0 GCB, 2 MCB, 12 AUTO READY, 14 GENSET, 16 TEST, 18 MAN/RUN, 20 AUTO, 22 STOP, 24 MAINS.
    # Value 1/2 = LED lit yellow/green
    result["panel_led_status"] = make_measurement((data[117:125].hex().upper(), data, 125, "N/A"), "")

    # Fuel (offset 585): tank capacity in liters; current liters derived from fuel level percent
    tank_capacity = read_number(data, 585, 2, 1, False)
    fuel_level = result["fuel_level_percent"]["value"]
    if isinstance(tank_capacity, int) and isinstance(fuel_level, (int, float)):
        result["fuel_tank_capacity_liters"] = make_measurement(tank_capacity, "lt.")
        result["fuel_status_liters"] = make_measurement(round(tank_capacity * fuel_level / 100.0, 1), "lt.")
    else:
        result["fuel_status_liters"] = make_measurement(tank_capacity, "lt.")

    # Hours To Go (template Extras GSK_H2G) is computed by Datakom software, not sent by the controller.
    # Offset 587 holds the full-load fuel rate (l/h); scaling it by apparent power / rated power
    # reproduces the portal value (222 lt, 27.7 kVA, 35 l/h, 100 kW -> 22.9 h vs 22.7 on the portal).
    full_load_rate = read_number(data, 587, 2, 1, False)
    liters = result["fuel_status_liters"]["value"]
    apparent_power = result["genset_S_total_kVA"]["value"]
    rated_power = result["engine_power_rate_percent"]["value"]
    hours_to_go = None
    if all(isinstance(v, (int, float)) and v > 0 for v in (full_load_rate, liters, apparent_power, rated_power)):
        hours_to_go = round(liters / (full_load_rate * apparent_power / rated_power), 1)
    result["full_load_fuel_rate"] = make_measurement(full_load_rate, "lt./h")
    result["hours_to_go"] = make_measurement(hours_to_go, "hour")


    # Analog sender slots (offset 255 + 19*i, template TipTag 11): int16 value /10,
    # 1 byte sender type, 16 bytes name ("    SENDER-1    "). 0x7FFF = not fitted.
    for i, key in enumerate(SENDER_KEYS):
        offset = 255 + i * 19
        if len(data) < offset + 19:
            break
        sender_type = data[offset + 2]
        result[key] = make_measurement(read_number(data, offset, 2, 10, True), SENDER_UNITS.get(sender_type, ""))

    # Active alarm texts (template AlarmHead=407, AlarmSize=96): '|'-separated sections,
    # messages inside a section are NUL-terminated ASCII strings.
    alerts = {
        "shutDown": [],
        "warning": [],
        "loadDump": []
    }
    sections = data[ALARM_HEAD:ALARM_HEAD + ALARM_SIZE].split(b"|")[1:]
    for section_idx, section in enumerate(sections):
        for raw_msg in section.split(b"\x00"):
            message = raw_msg.decode("ascii", errors="ignore").strip()
            if not message:
                continue
            alarm_index = get_alarm_index_by_message(message)
            if alarm_index != -1:
                alerts[get_alert_category_by_index(alarm_index)].append(alarm_index)
            else:
                # Unknown text: assume section order shutdown | loaddump | warning (not yet verified
                # on a live alarm); keep the raw text so it is still reported
                category = ALARM_SECTION_ORDER[min(section_idx, len(ALARM_SECTION_ORDER) - 1)]
                alerts[category].append(message)

    # Store alerts separately (not in telemetry result)
    result["_alerts_internal"] = alerts
    
    return result


def decode_unknown_offsets(data: bytes) -> dict:
    """Parse all unknown/unused offset ranges from telemetry packet"""
    
    if len(data) < 300:
        return {"error": f"Packet too short: {len(data)} bytes"}
    
    result = {}
    
    # Range 16-18 (2 bytes)
    if len(data) > 18:
        result["offset_16_18"] = make_measurement(data[16:18].hex())
    
    # Range 20-21 (1 byte)
    if len(data) > 21:
        result["offset_20"] = make_measurement(data[20])
    
    # Range 33-37 (4 bytes)
    if len(data) > 37:
        result["offset_33_37"] = make_measurement(data[33:37].hex())
    
    # Range 41-56 (15 bytes)
    if len(data) > 56:
        result["offset_41_56"] = make_measurement(data[41:56].hex())
    
    # Range 88-99 (11 bytes)
    if len(data) > 99:
        result["offset_88_99"] = make_measurement(data[88:99].hex())
    
    # Range 101-103 (2 bytes)
    if len(data) > 103:
        result["offset_101"] = make_measurement(data[101])
        result["offset_102"] = make_measurement(data[102])
    
    # Range 104 (1 byte) - between state and Mode
    if len(data) > 104:
        result["offset_104"] = make_measurement(data[104])
    
    # Range 106-181 (75 bytes) - large unknown block before voltages
    if len(data) > 181:
        # Split into smaller chunks for readability
        result["offset_106_116"] = make_measurement(data[106:116].hex())
        result["offset_116_126"] = make_measurement(data[116:126].hex())
        result["offset_126_136"] = make_measurement(data[126:136].hex())
        result["offset_136_146"] = make_measurement(data[136:146].hex())
        result["offset_146_156"] = make_measurement(data[146:156].hex())
        result["offset_156_166"] = make_measurement(data[156:166].hex())
        result["offset_166_176"] = make_measurement(data[166:176].hex())
        result["offset_176_181"] = make_measurement(data[176:181].hex())
    
    # Range 249-258 (9 bytes) - between fuel level and SENDER slots
    if len(data) > 258:
        result["offset_249_258"] = make_measurement(data[249:258].hex())
    
    # Range 513-539 (26 bytes) - between engine hours and total kWh
    if len(data) > 539:
        result["offset_513_520"] = make_measurement(data[513:520].hex())
        result["offset_520_530"] = make_measurement(data[520:530].hex())
        result["offset_530_539"] = make_measurement(data[530:539].hex())
    
    # Range 543-592 (49 bytes) - between total kWh and MAC address
    if len(data) > 592:
        result["offset_543_550"] = make_measurement(data[543:550].hex())
        result["offset_550_560"] = make_measurement(data[550:560].hex())
        result["offset_560_570"] = make_measurement(data[560:570].hex())
        result["offset_570_580"] = make_measurement(data[570:580].hex())
        result["offset_580_590"] = make_measurement(data[580:590].hex())
        result["offset_590_592"] = make_measurement(data[590:592].hex())
    
    # Range 598-640 (42 bytes) - after MAC address to end of packet
    if len(data) > 598:
        result["offset_598_608"] = make_measurement(data[598:608].hex())
        result["offset_608_618"] = make_measurement(data[608:618].hex())
        result["offset_618_628"] = make_measurement(data[618:628].hex())
        result["offset_628_638"] = make_measurement(data[628:638].hex())
        result["offset_638_640"] = make_measurement(data[638:640].hex())
    
    return result


def format_telemetry(decoded: dict) -> str:
    """Format decoded telemetry for console output"""
    
    if "error" in decoded:
        return f"ERROR: {decoded['error']}"
    
    lines = []
    lines.append("=" * 70)
    lines.append("DATAKOM D500 MK3 TELEMETRY")
    lines.append("=" * 70)
    
    if "generator_name" in decoded:
        lines.append(f"Generator: {decoded['generator_name']['value']}")
    
    if "unique_id" in decoded:
        lines.append(f"UniqueID: {decoded['unique_id']['value']}")
    
    if "mac_address" in decoded:
        lines.append(f"MAC Address: {decoded['mac_address']['value']}")
    
    if "lan_ip" in decoded:
        lines.append(f"LAN IP: {decoded['lan_ip']['value']}")
    
    if "modbus_port" in decoded:
        lines.append(f"ModBus Port: {decoded['modbus_port']['value']}")
    
    lines.append(f"Mode: {decoded['mode']['value']} ({decoded['mode_name']['value']})")
    lines.append(f"State: {decoded['state']['value']} ({decoded['state_name']['value']})")
    
    lines.append(f"Device Date: {decoded['device_date']['value']}")
    
    if "engine_run_hours_total" in decoded:
        lines.append(f"Total Engine Hours: {decoded['engine_run_hours_total']['value']} {decoded['engine_run_hours_total']['unit']}")
    
    if "total_kWh" in decoded:
        lines.append(f"Total Energy: {decoded['total_kWh']['value']} {decoded['total_kWh']['unit']}")
    
    lines.append("")
    
    lines.append("GENSET:")
    lines.append(f"  Voltage L1:     {decoded['genset_L1_V']['value']} {decoded['genset_L1_V']['unit']}")
    lines.append(f"  Voltage L2:     {decoded['genset_L2_V']['value']} {decoded['genset_L2_V']['unit']}")
    lines.append(f"  Voltage L3:     {decoded['genset_L3_V']['value']} {decoded['genset_L3_V']['unit']}")
    lines.append(f"  Voltage L1-L2:  {decoded['genset_L1_L2_V']['value']} {decoded['genset_L1_L2_V']['unit']}")
    lines.append(f"  Voltage L2-L3:  {decoded['genset_L2_L3_V']['value']} {decoded['genset_L2_L3_V']['unit']}")
    lines.append(f"  Voltage L3-L1:  {decoded['genset_L3_L1_V']['value']} {decoded['genset_L3_L1_V']['unit']}")
    lines.append(f"  Current I1:     {decoded['genset_I1_A']['value']} {decoded['genset_I1_A']['unit']}")
    lines.append(f"  Current I2:     {decoded['genset_I2_A']['value']} {decoded['genset_I2_A']['unit']}")
    lines.append(f"  Current I3:     {decoded['genset_I3_A']['value']} {decoded['genset_I3_A']['unit']}")
    lines.append(f"  Frequency:      {decoded['genset_freq_Hz']['value']} {decoded['genset_freq_Hz']['unit']}")
    lines.append(f"  Active Power:   {decoded['genset_P_total_kW']['value']} {decoded['genset_P_total_kW']['unit']}")
    lines.append(f"  Apparent Power: {decoded['genset_S_total_kVA']['value']} {decoded['genset_S_total_kVA']['unit']}")
    lines.append("")
    
    lines.append("ENGINE:")
    lines.append(f"  RPM:            {decoded['engine_rpm']['value']} {decoded['engine_rpm']['unit']}")
    lines.append(f"  Battery:        {decoded['battery_voltage_Vdc']['value']} {decoded['battery_voltage_Vdc']['unit']}")
    lines.append(f"  Oil Pressure:   {decoded['oil_pressure_bar']['value']} {decoded['oil_pressure_bar']['unit']}")
    lines.append(f"  Coolant Temp:   {decoded['coolant_temp_C']['value']}{decoded['coolant_temp_C']['unit']}")
    lines.append(f"  Fuel Level:     {decoded['fuel_level_percent']['value']}{decoded['fuel_level_percent']['unit']}")
    
    if decoded.get("_alerts_internal"):
        alerts = decoded["_alerts_internal"]
        
        if alerts["shutDown"]:
            lines.append("")
            lines.append("⛔ SHUTDOWN ALERTS:")
            for msg in alerts["shutDown"]:
                lines.append(f"  - {msg}")
        
        if alerts["warning"]:
            lines.append("")
            lines.append("⚠ WARNINGS:")
            for msg in alerts["warning"]:
                lines.append(f"  - {msg}")
        
        if alerts["loadDump"]:
            lines.append("")
            lines.append("🔻 LOAD DUMP ALERTS:")
            for msg in alerts["loadDump"]:
                lines.append(f"  - {msg}")
    
    lines.append("=" * 70)
    
    return "\n".join(lines)
