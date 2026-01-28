"""
Decoder for Datakom D500 MK3 telemetry packets
"""

from datakom_constants import (
    MODE_NAMES, STATE_NAMES, get_alert_category,
    SENDER_FLAG_HAS_MESSAGE, ALERT_CATEGORY_NOT_USED
)


def make_measurement(value, unit=""):
    """Create measurement object with value and unit"""
    return {
        "value": value,
        "unit": unit
    }


def decode_telemetry(data: bytes) -> dict:
    """Decode telemetry packet from Datakom D500 MK3 controller"""
    
    if len(data) < 300:
        return {"error": f"Packet too short: {len(data)} bytes"}
    
    result = {}
    
    # Header
    result["header"] = make_measurement(data[0:8].decode("ascii", errors="ignore"))
    
    # Protocol version / packet type (offset 8-15)
    result["protocol_info"] = make_measurement(data[8:16].hex())
    
    # ModBus port (offset 18-19, big-endian)
    result["modbus_port"] = make_measurement(int.from_bytes(data[18:20], "big"))
    
    # UniqueID (offset 21-32, hex string)
    result["unique_id"] = make_measurement(data[21:33].hex().upper())
    
    # LAN IP (offset 37-40)
    result["lan_ip"] = make_measurement(".".join(str(b) for b in data[37:41]))
    
    # WAN IP (offset 598-601, if available)
    if len(data) > 601:
        result["wan_ip"] = make_measurement(".".join(str(b) for b in data[598:602]))
    
    # Generator name (offset 56-87)
    result["generator_name"] = make_measurement(data[56:88].decode("ascii", errors="ignore").strip('\x00- '))
    
    # GPS coordinates (offset 45-52, 4 bytes each, scaled by 1000000)
    if len(data) > 52:
        lat_raw = int.from_bytes(data[45:49], "little")
        result["latitude"] = make_measurement(round(lat_raw / 1000000, 6), "")
        
        lon_raw = int.from_bytes(data[49:53], "little")
        result["longitude"] = make_measurement(round(lon_raw / 1000000, 6), "")
    
    # Mode (offset 103)
    mode_code = data[103]
    result["mode"] = make_measurement(mode_code)
    result["mode_name"] = make_measurement(MODE_NAMES.get(mode_code, f"Unknown ({mode_code})"))
    
    # State (offset 105)
    state_code = data[105]
    result["state"] = make_measurement(state_code)
    result["state_name"] = make_measurement(STATE_NAMES.get(state_code, f"Unknown ({state_code})"))
    
    # MAC Address (offset 592-597, if packet is long enough)
    if len(data) > 597:
        result["mac_address"] = make_measurement(data[592:598].hex().upper())
    
    # Runtime counter (offset 99-100) - minutes of current session
    runtime_raw = int.from_bytes(data[99:101], "little")
    result["runtime_counter_minutes"] = make_measurement(runtime_raw, "minutes")
    result["runtime_hours"] = make_measurement(round(runtime_raw / 60, 2), "hour")
    
    # Genset voltages (offset 181, 185, 189) - scaled by 10
    result["genset_L1_V"] = make_measurement(round(int.from_bytes(data[181:183], "little") / 10, 1), "V")
    result["genset_L2_V"] = make_measurement(round(int.from_bytes(data[185:187], "little") / 10, 1), "V")
    result["genset_L3_V"] = make_measurement(round(int.from_bytes(data[189:191], "little") / 10, 1), "V")
    
    # Genset currents (offset 193, 197, 201) - scaled by 10
    result["genset_I1_A"] = make_measurement(round(int.from_bytes(data[193:195], "little") / 10, 1), "A")
    result["genset_I2_A"] = make_measurement(round(int.from_bytes(data[197:199], "little") / 10, 1), "A")
    result["genset_I3_A"] = make_measurement(round(int.from_bytes(data[201:203], "little") / 10, 1), "A")
    
    # Line-to-line voltages (offset 205, 209, 213) - scaled by 10
    result["genset_L1_L2_V"] = make_measurement(round(int.from_bytes(data[205:207], "little") / 10, 1), "V")
    result["genset_L2_L3_V"] = make_measurement(round(int.from_bytes(data[209:211], "little") / 10, 1), "V")
    result["genset_L3_L1_V"] = make_measurement(round(int.from_bytes(data[213:215], "little") / 10, 1), "V")
    
    # Active Power (offset 217) - kW, scaled by 10
    result["genset_P_total_kW"] = make_measurement(round(int.from_bytes(data[217:219], "little") / 10, 1), "kW")
    
    # Apparent Power (offset 225) - kVA, scaled by 10
    result["genset_S_total_kVA"] = make_measurement(round(int.from_bytes(data[225:227], "little") / 10, 1), "kVA")
    
    # Frequency (offset 231) - Hz, scaled by 100
    result["genset_freq_Hz"] = make_measurement(round(int.from_bytes(data[231:233], "little") / 100, 2), "Hz")
    
    # Mains voltages (offset 125, 129, 133) - scaled by 10
    if len(data) > 135:
        result["mains_L1_V"] = make_measurement(round(int.from_bytes(data[125:127], "little") / 10, 1), "V")
        result["mains_L2_V"] = make_measurement(round(int.from_bytes(data[129:131], "little") / 10, 1), "V")
        result["mains_L3_V"] = make_measurement(round(int.from_bytes(data[133:135], "little") / 10, 1), "V")
    
    # Mains currents (offset 137, 141, 145) - scaled by 10
    if len(data) > 147:
        result["mains_I1_A"] = make_measurement(round(int.from_bytes(data[137:139], "little") / 10, 1), "A")
        result["mains_I2_A"] = make_measurement(round(int.from_bytes(data[141:143], "little") / 10, 1), "A")
        result["mains_I3_A"] = make_measurement(round(int.from_bytes(data[145:147], "little") / 10, 1), "A")
    
    # Mains line-to-line voltages (offset 149, 153, 157) - scaled by 10
    if len(data) > 159:
        result["mains_L1_L2_V"] = make_measurement(round(int.from_bytes(data[149:151], "little") / 10, 1), "V")
        result["mains_L2_L3_V"] = make_measurement(round(int.from_bytes(data[153:155], "little") / 10, 1), "V")
        result["mains_L3_L1_V"] = make_measurement(round(int.from_bytes(data[157:159], "little") / 10, 1), "V")
    
    # Mains power (offset 161, 165, 169) - scaled by 10
    if len(data) > 171:
        result["mains_P_total_kW"] = make_measurement(round(int.from_bytes(data[161:163], "little") / 10, 1), "kW")
        result["mains_Q_total_kVAr"] = make_measurement(round(int.from_bytes(data[165:167], "little") / 10, 1), "kVAr")
        result["mains_S_total_kVA"] = make_measurement(round(int.from_bytes(data[169:171], "little") / 10, 1), "kVA")
    
    # Mains frequency (offset 175) - Hz, scaled by 100
    if len(data) > 177:
        result["mains_freq_Hz"] = make_measurement(round(int.from_bytes(data[175:177], "little") / 100, 2), "Hz")
    
    # Engine RPM (offset 237)
    result["engine_rpm"] = make_measurement(int.from_bytes(data[237:239], "little"), "RPM")
    
    # Battery voltage (offset 239) - V, scaled by 100
    result["battery_voltage_Vdc"] = make_measurement(round(int.from_bytes(data[239:241], "little") / 100, 2), "Vdc")
    
    # Charge voltage (offset 241) - V, scaled by 100
    if len(data) > 243:
        result["charge_voltage"] = make_measurement(round(int.from_bytes(data[241:243], "little") / 100, 2), "Vdc")
    
    # Oil pressure (offset 243) - bar, scaled by 10
    result["oil_pressure_bar"] = make_measurement(round(int.from_bytes(data[243:245], "little") / 10, 1), "Bar")
    
    # Coolant temperature (offset 245) - Celsius, scaled by 10
    result["coolant_temp_C"] = make_measurement(round(int.from_bytes(data[245:247], "little") / 10, 1), "'C")
    
    # Fuel level (offset 247) - percent, scaled by 10
    result["fuel_level_percent"] = make_measurement(round(int.from_bytes(data[247:249], "little") / 10, 1), "%")
    
    # Oil temperature (offset 249) - Celsius, scaled by 10
    if len(data) > 251:
        result["oil_temp"] = make_measurement(round(int.from_bytes(data[249:251], "little") / 10, 1), "'C")
    
    # Canopy temperature (offset 251) - Celsius, scaled by 10
    if len(data) > 253:
        result["canopy_temp"] = make_measurement(round(int.from_bytes(data[251:253], "little") / 10, 1), "'C")
    
    # Alerts structure (offset 258-500)
    # SENDER slots: 8 slots × 19 bytes each (258-407)
    # Each slot has: 16 bytes name + 3 bytes flags
    # Flags structure (from DK_Serbian.c):
    #   [0]: Status/count (varies)
    #   [1]: Message indicator (0x01=has message, 0x03=configured, 0x7F=inactive)
    #   [2]: Category (ASCII char: '3'=warning, '4'=notUsed, '5'=shutDown, '6'=loadDump)
    # After SENDER slots come alert messages (starting ~413)
    # Messages appear in order of SENDER slots with flag[1]=0x01
    
    alerts = {
        "shutDown": [],
        "warning": [],
        "loadDump": []
    }
    
    # Parse SENDER slots to find active categories with messages
    active_slots = []
    for i in range(8):
        offset = 258 + (i * 19)
        if offset + 19 <= len(data):
            slot_name = data[offset:offset+16].decode('ascii', errors='ignore').strip()
            flags = data[offset+16:offset+19]
            
            if not slot_name.startswith("SENDER"):
                continue
            
            flag0, flag1, flag2 = flags[0], flags[1], flags[2]
            
            # Check if this slot has an active message (use bitmask to be robust)
            has_message = (flag1 & SENDER_FLAG_HAS_MESSAGE) == SENDER_FLAG_HAS_MESSAGE
            
            if has_message:
                # Get category from flag[2] using constants
                category = get_alert_category(flag2)
                
                # Skip "notUsed" category
                if category != ALERT_CATEGORY_NOT_USED and category in alerts:
                    active_slots.append((category, i))
    
    # Parse messages after SENDER slots
    # Messages start at offset 413 and occupy the region before statistics
    # They are pipe '|' separated; read the whole region and split into parts
    message_start = 413
    message_end = min(len(data), 503)  # stop before statistics area
    raw_msgs = data[message_start:message_end]

    try:
        decoded_msgs = raw_msgs.decode('ascii', errors='ignore')
    except Exception:
        decoded_msgs = ''

    parts = [p.strip() for p in decoded_msgs.split('|') if p.strip()]
    messages = []
    for part in parts:
        part_clean = part.replace('\x00', '').strip()
        if len(part_clean) > 0:
            messages.append(part_clean)
    
    # Match messages to active categories
    for idx, (category, slot_num) in enumerate(active_slots):
        if idx < len(messages):
            alerts[category].append(messages[idx])
    
    # Store alerts separately (not in telemetry result)
    result["_alerts_internal"] = alerts
    
    # Genset statistics (offset 503-549)
    if len(data) > 504:
        result["genset_starts_count"] = make_measurement(int.from_bytes(data[503:505], "little"), "")
    
    if len(data) > 510:
        result["reactive_energy_inductive"] = make_measurement(round(int.from_bytes(data[507:511], "little") / 10, 1), "kVArh")
    
    # Engine run hours total (offset 511) - hours, scaled by 100
    if len(data) > 512:
        result["engine_run_hours_total"] = make_measurement(round(int.from_bytes(data[511:513], "little") / 100, 2), "hour")
    
    # Service intervals (offset 515-536)
    if len(data) > 516:
        result["hours_to_service_1"] = make_measurement(round(int.from_bytes(data[515:517], "little") / 100, 2), "hour")
    
    if len(data) > 522:
        result["days_to_service_1"] = make_measurement(round(int.from_bytes(data[519:523], "little") / 100, 2), "day")
    
    if len(data) > 524:
        result["hours_to_service_2"] = make_measurement(round(int.from_bytes(data[523:525], "little") / 100, 2), "hour")
    
    if len(data) > 528:
        result["days_to_service_2"] = make_measurement(round(int.from_bytes(data[527:531], "little") / 100, 2), "day")
    
    if len(data) > 532:
        result["hours_to_service_3"] = make_measurement(round(int.from_bytes(data[531:533], "little") / 100, 2), "hour")
    
    if len(data) > 536:
        result["days_to_service_3"] = make_measurement(round(int.from_bytes(data[535:539], "little") / 100, 2), "day")
    
    # Total energy produced (offset 539) - kWh, scaled by 10
    if len(data) > 542:
        result["total_kWh"] = make_measurement(round(int.from_bytes(data[539:543], "little") / 10, 1), "kWh")
    
    # Genset cranks count (offset 543)
    if len(data) > 544:
        result["genset_cranks_count"] = make_measurement(int.from_bytes(data[543:545], "little"), "")
    
    # Reactive energy capacitive (offset 547)
    if len(data) > 548:
        result["reactive_energy_capacitive"] = make_measurement(round(int.from_bytes(data[547:549], "little") / 10, 1), "kVArh")
    
    # Engine power rate (offset 553) - percent
    if len(data) > 554:
        result["engine_power_rate_percent"] = make_measurement(int.from_bytes(data[553:555], "little"), "%")
    
    # Battery voltage 2 (offset 555) - V, scaled by 100
    if len(data) > 557:
        result["battery_voltage_2_Vdc"] = make_measurement(round(int.from_bytes(data[555:557], "little") / 100, 2), "Vdc")
    
    # Mains energy counters (offset 561-576)
    if len(data) > 565:
        result["mains_total_kWh"] = make_measurement(round(int.from_bytes(data[561:565], "little") / 10, 1), "kWh")
    
    if len(data) > 569:
        result["mains_total_kVArh_ind"] = make_measurement(round(int.from_bytes(data[565:569], "little") / 10, 1), "kVArh")
    
    if len(data) > 573:
        result["mains_total_kVArh_cap"] = make_measurement(round(int.from_bytes(data[569:573], "little") / 10, 1), "kVArh")
    
    if len(data) > 577:
        result["mains_total_export_kWh"] = make_measurement(round(int.from_bytes(data[573:577], "little") / 10, 1), "kWh")
    
    # Fuel consumption FlowMeter (offset 577) - liters, scaled by 10
    if len(data) > 581:
        result["fuel_consumption_flowm"] = make_measurement(round(int.from_bytes(data[577:581], "little") / 10, 1), "lt.")
    
    # Fuel status (offset 585) - liters
    # NOTE: this field overlaps older/uncertain offsets; read as 2 bytes to avoid
    # colliding with the separate `fuel_percent` 2-byte field at 587-588.
    if len(data) > 587:
        # bytes at 585:587 hold tank capacity (liters). compute current liters
        tank_capacity = int.from_bytes(data[585:587], "little")
        result["fuel_tank_capacity_liters"] = make_measurement(tank_capacity, "lt.")
        # compute current fuel liters using fuel level percent if available
        flp = None
        if isinstance(result.get("fuel_level_percent"), dict):
            flp = result.get("fuel_level_percent").get("value")
        if flp is not None:
            try:
                current_liters = round(tank_capacity * (float(flp) / 100.0), 1)
            except Exception:
                current_liters = None
        else:
            current_liters = None
        # Preserve legacy key `fuel_status_liters` as the current liters for API compatibility
        result["fuel_status_liters"] = make_measurement(current_liters if current_liters is not None else tank_capacity, "lt.")

    # Fuel percent (offset 587) - percent (2 bytes)
    if len(data) > 589:
        result["fuel_percent"] = make_measurement(int.from_bytes(data[587:589], "little"), "%")
    
    # GPS satellites (offset 589)
    if len(data) > 590:
        result["satellites"] = make_measurement(int.from_bytes(data[589:590], "little"), "")
    
    # Fuel consumption ECU (offset 598) - liters, scaled by 10
    if len(data) > 602:
        result["fuel_consumption_ecu"] = make_measurement(round(int.from_bytes(data[598:602], "little") / 10, 1), "lt.")
    
    # Battery group parameters (offset 602-610)
    if len(data) > 604:
        result["min_battery_voltage"] = make_measurement(round(int.from_bytes(data[602:604], "little") / 100, 2), "Vdc")
    
    if len(data) > 606:
        result["battery_group_voltage"] = make_measurement(round(int.from_bytes(data[604:606], "little") / 100, 2), "Vdc")
    
    if len(data) > 608:
        result["battery_group_current"] = make_measurement(round(int.from_bytes(data[606:608], "little") / 10, 1), "A")
    
    if len(data) > 612:
        result["discharge_current_counter"] = make_measurement(int.from_bytes(data[608:612], "little"), "")
    
    # Fuel rate FlowMeter (offset 612) - l/h, scaled by 10
    if len(data) > 614:
        result["fuel_rate_flowm"] = make_measurement(round(int.from_bytes(data[612:614], "little") / 10, 1), "lt./h")
    
    # Fuel rate ECU (offset 614) - l/h, scaled by 10
    if len(data) > 616:
        result["fuel_rate_ecu"] = make_measurement(round(int.from_bytes(data[614:616], "little") / 10, 1), "lt./h")
    
    # DC alternator and battery (offset 616-625)
    if len(data) > 618:
        result["alternator_voltage"] = make_measurement(round(int.from_bytes(data[616:618], "little") / 100, 2), "Vdc")
    
    if len(data) > 620:
        result["load_battery_voltage"] = make_measurement(round(int.from_bytes(data[618:620], "little") / 100, 2), "Vdc")
    
    if len(data) > 622:
        result["dc_actual_current"] = make_measurement(round(int.from_bytes(data[620:622], "little") / 10, 1), "A")
    
    if len(data) > 624:
        result["dc_battery_temp"] = make_measurement(round(int.from_bytes(data[622:624], "little") / 10, 1), "'C")
    
    if len(data) > 626:
        result["dc_charge_state"] = make_measurement(int.from_bytes(data[624:626], "little"), "")
    
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
    
    lines.append(f"Session Runtime: {decoded['runtime_hours']['value']} {decoded['runtime_hours']['unit']} ({decoded['runtime_counter_minutes']['value']} {decoded['runtime_counter_minutes']['unit']})")
    
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
