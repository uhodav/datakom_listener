"""
Parameter ID and label mapping for D500 MK3
Maps telemetry keys to fixed parameter IDs as per API specification
"""

# Mapping: telemetry_key -> (id, label)
PARAM_MAPPING = {
    # Genset Mode & State
    "mode": (103, "Genset Mode"),
    "state": (105, "Genset State"),
    
    # Genset Voltages
    "genset_L1_V": (181, "Genset L1"),
    "genset_L2_V": (185, "Genset L2"),
    "genset_L3_V": (189, "Genset L3"),
    "genset_L1_L2_V": (205, "Genset L1-L2"),
    "genset_L2_L3_V": (209, "Genset L2-L3"),
    "genset_L3_L1_V": (213, "Genset L3-L1"),
    
    # Genset Currents
    "genset_I1_A": (193, "Genset I1"),
    "genset_I2_A": (197, "Genset I2"),
    "genset_I3_A": (201, "Genset I3"),
    
    # Genset Power & Frequency
    "genset_freq_Hz": (231, "Genset Freq"),
    "genset_in": (233, "Genset In"),
    "genset_power_factor": (229, "Genset Pwr Factor"),
    "genset_P_total_kW": (217, "Genset Tot Active Pwr"),
    "genset_Q_total_kVAr": (221, "Genset Tot Reactive Pwr"),
    "genset_S_total_kVA": (225, "Genset Tot Apparent Pwr"),
    
    # Genset Energy Counters
    "total_kWh": (539, "Genset Total kWh"),
    "reactive_energy_inductive": (543, "Genset Total kVArh (Ind)"),
    "reactive_energy_capacitive": (547, "Genset Total kVArh (Cap)"),
    "engine_power_rate_percent": (553, "Genset Engine Pwr Rate"),
    
    # Mains Voltages
    "mains_L1_V": (125, "Mains L1"),
    "mains_L2_V": (129, "Mains L2"),
    "mains_L3_V": (133, "Mains L3"),
    "mains_L1_L2_V": (149, "Mains L1-L2"),
    "mains_L2_L3_V": (153, "Mains L2-L3"),
    "mains_L3_L1_V": (157, "Mains L3-L1"),
    
    # Mains Currents
    "mains_I1_A": (137, "Mains I1"),
    "mains_I2_A": (141, "Mains I2"),
    "mains_I3_A": (145, "Mains I3"),
    
    # Mains Power & Frequency
    "mains_freq_Hz": (175, "Mains Freq"),
    "mains_in": (177, "Mains In"),
    "mains_power_factor": (173, "Mains Pwr Factor"),
    "mains_P_total_kW": (161, "Mains Tot Active Pwr"),
    "mains_Q_total_kVAr": (165, "Mains Tot Reactive Pwr"),
    "mains_S_total_kVA": (169, "Mains Tot Apparent Pwr"),
    
    # Mains Energy Counters
    "mains_total_kWh": (561, "Mains Total kWh"),
    "mains_total_kVArh_ind": (565, "Mains Total kVArh (Ind)"),
    "mains_total_kVArh_cap": (569, "Mains Total kVArh (Cap)"),
    "mains_total_export_kWh": (573, "Mains Total Export kWh"),
    
    # Engine Parameters
    "battery_voltage_Vdc": (239, "Engine Battery Voltage1"),
    "battery_voltage_2_Vdc": (555, "Engine Battery Voltage2"),
    "charge_voltage": (241, "Engine Charge Voltage"),
    "engine_rpm": (237, "Engine RPM"),
    "oil_pressure_bar": (243, "Engine Oil Pressure"),
    "coolant_temp_C": (245, "Engine Coolant Temp"),
    "oil_temp": (249, "Engine Oil Temp"),
    "canopy_temp": (251, "Engine Canopy Temp"),
    "fuel_level_percent": (247, "Engine Fuel Level"),
    "fuel_status_liters": (585, "Engine Fuel Status"),
    
    # Engine Alternator & Battery
    "alternator_voltage": (616, "Engine Alternator Voltage"),
    "load_battery_voltage": (618, "Engine Load Battery Voltage"),
    "dc_actual_current": (620, "Engine DC Actual Current"),
    "dc_battery_temp": (622, "Engine DC Battery Temp"),
    "dc_charge_state": (624, "Engine Charge State"),
    
    # Engine Counters
    "genset_starts_count": (503, "Engine Genset Runs"),
    "genset_cranks_count": (507, "Engine Genset Cranks"),
    "engine_run_hours_total": (511, "Engine Run Hours"),
    
    # Engine Service Intervals
    "hours_to_service_1": (515, "Engine Hours to Srv1"),
    "days_to_service_1": (519, "Engine Days to Srv1"),
    "hours_to_service_2": (523, "Engine Hours to Srv2"),
    "days_to_service_2": (527, "Engine Days to Srv2"),
    "hours_to_service_3": (531, "Engine Hours to Srv3"),
    "days_to_service_3": (535, "Engine Days to Srv3"),
    "hours_to_go": (587, "Engine Hours to Go"),
    
    # Engine Fuel (ECU)
    "fuel_consumption_ecu": (598, "Engine Fuel Consumption (ECU)"),
    "fuel_rate_ecu": (614, "Engine Fuel Rate(ECU)"),
    
    # Engine Fuel (FlowMeter)
    "fuel_consumption_flowm": (577, "Engine Fuel Consump(FlowM)"),
    "fuel_rate_flowm": (612, "Engine Fuel Rate(FlowM)"),
    
    # Sender Values
    "sender_oil_pressure": (255, "SENDER oil pressure"),
    "sender_engine_temp": (274, "SENDER engine temp"),
    "sender_fuel_level_1": (293, "SENDER fuel level"),
    "sender_fuel_level_2": (312, "SENDER fuel level"),
    
    # Information - Network
    "lan_ip": (37, "Information LAN-IP"),
    "wan_ip": (33, "Information WAN-IP"),
    "gsm_ip": (41, "Information GSM-IP"),
    "site_id": (57, "Information SITE-ID"),
    "engine_serial": (78, "Information Engine Serial"),
    
    # Information - Device
    "device_type": (9, "Information Device Type"),
    "sw_version": (11, "Information SW Version"),
    "hw_version": (13, "Information HW Version"),
    "unique_id": (21, "Information UniqueID"),
    "device_date": (99, "Information Device Date"),
    "device_time": (99, "Information Device Time"),
    "last_update_date": (10005, "Information Last Update Date"),
    "last_update_time": (10005, "Information Last Update Time"),
    
    # Information - GPS
    "latitude": (10002, "Information Latitude"),
    "longitude": (10003, "Information Longitude"),
    "satellites": (589, "Information Satellite(s)"),
    
    # Information - ModBus
    "modbus_addr": (18, "Information ModBus Addr"),
    "modbus_port": (19, "Information ModBus Port"),
    "connection": (8, "Information Connection"),
    
    # Information - Network Addresses
    "mac_reset": (590, "Information MAC-Rst"),
    "mac_address": (592, "Information MAC-Adr"),
    "information": (581, "Information"),
    
    # Information - Battery Group
    "min_battery_voltage": (602, "Information Min Battery Voltage"),
    "battery_group_voltage": (604, "Information Battery Group Voltage"),
    "battery_group_current": (606, "Information Battery Group Current"),
    "discharge_current_counter": (608, "Information Discharge Current Counter"),
    
    # GPS and Network
    "latitude": (45, "GPS Latitude"),
    "longitude": (49, "GPS Longitude"),
    "satellites": (589, "GPS Satellites"),
}


def get_param_id_label(key: str) -> tuple:
    """
    Get parameter ID and label for telemetry key
    
    Args:
        key: Telemetry parameter key
        
    Returns:
        Tuple of (id, label). Returns (0, key) if not found in mapping.
    """
    return PARAM_MAPPING.get(key, (0, key))


def get_all_param_names() -> list:
    """
    Get all parameter IDs and labels sorted by ID
    
    Returns:
        List of dicts with 'id' and 'label' keys
    """
    # Get unique (id, label) pairs
    unique_params = {}
    for key, (param_id, label) in PARAM_MAPPING.items():
        if param_id not in unique_params:
            unique_params[param_id] = label
    
    # Sort by ID and return as list
    params = [
        {"id": param_id, "label": label}
        for param_id, label in sorted(unique_params.items())
    ]
    
    return params
