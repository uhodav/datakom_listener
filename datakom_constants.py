"""
Datakom D500 MK3 Protocol Constants
"""

import os
from config import DEFAULT_LANGUAGE

# =============================================================================
# LANGUAGE SUPPORT
# =============================================================================
LANGUAGE = os.environ.get('DATAKOM_LANG', DEFAULT_LANGUAGE)

def _load_translations():
    """Load language-specific translations"""
    try:
        if LANGUAGE == 'ru':
            from lang import ru as translations
        elif LANGUAGE == 'en':
            from lang import en as translations
        else:
            from lang import uk as translations
        return translations
    except ImportError:
        # Fallback to Ukrainian if language file not found
        from lang import uk as translations
        return translations

_translations = _load_translations()

MODE_NAMES = _translations.MODE_NAMES
STATE_NAMES = _translations.STATE_NAMES
ENGINE_STATE_NAMES = _translations.ENGINE_STATE_NAMES
BREAKER_STATE_NAMES = _translations.BREAKER_STATE_NAMES
MAINS_STATE_NAMES = _translations.MAINS_STATE_NAMES
BATTERY_STATE_NAMES = _translations.BATTERY_STATE_NAMES
START_SOURCE_NAMES = _translations.START_SOURCE_NAMES
RUNNING_TYPE_NAMES = _translations.RUNNING_TYPE_NAMES
ALARM_MESSAGES = _translations.ALARM_MESSAGES
OUTPUT_FUNCTIONS = _translations.OUTPUT_FUNCTIONS

# =============================================================================
# UNIT MODES (offset 103)
# =============================================================================
MODE_STOP = 0
MODE_AUTO = 1
MODE_MANUAL = 2
MODE_TEST = 3
MODE_AUTO_START = 4
MODE_REMOTE = 5
MODE_SCHEDULE = 6
MODE_MAINTENANCE = 7
MODE_EMERGENCY = 8

# =============================================================================
# GENSET STATES (offset 105)
# Based on D500 MK3 specification
# =============================================================================
STATE_AT_REST = 0
STATE_WAIT_BEFORE_FUEL = 1
STATE_ENGINE_PREHEAT = 2
STATE_WAIT_OIL_FLASH_OFF = 3
STATE_CRANK_REST = 4
STATE_CRANKING = 5
STATE_ENGINE_RUN_IDLE = 6
STATE_ENGINE_HEATING = 7
STATE_RUNNING_OFF_LOAD = 8
STATE_SYNCHRONIZING_TO_MAINS = 9
STATE_LOAD_TRANSFER_TO_GENSET = 10
STATE_GEN_CB_ACTIVATION = 11
STATE_GENSET_CB_TIMER = 12
STATE_MASTER_GENSET_ON_LOAD = 13
STATE_PEAK_LOPPING = 14
STATE_POWER_EXPORTING = 15
STATE_SLAVE_GENSET_ON_LOAD = 16
STATE_SYNCHRONIZING_BACK_TO_MAINS = 17
STATE_LOAD_TRANSFER_TO_MAINS = 18
STATE_MAINS_CB_ACTIVATION = 19
STATE_MAINS_CB_TIMER = 20
STATE_STOP_WITH_COOLDOWN = 21
STATE_COOLING_DOWN = 22
STATE_ENGINE_STOP_IDLE = 23
STATE_IMMEDIATE_STOP = 24
STATE_ENGINE_STOPPING = 25

# =============================================================================
# ENGINE STATES
# =============================================================================
ENGINE_STATE_OFF = 0
ENGINE_STATE_CRANKING = 1
ENGINE_STATE_RUNNING = 2
ENGINE_STATE_STOPPING = 3
ENGINE_STATE_FAILED_START = 4
ENGINE_STATE_STALLED = 5
ENGINE_STATE_OIL_PRESSURE_LOW = 6
ENGINE_STATE_HIGH_TEMPERATURE = 7
ENGINE_STATE_OVERSPEED = 8

# =============================================================================
# BREAKER STATES
# =============================================================================
BREAKER_STATE_BOTH_OPEN = 0
BREAKER_STATE_GENSET_CLOSED = 1
BREAKER_STATE_MAINS_CLOSED = 2
BREAKER_STATE_BOTH_CLOSED = 3

# =============================================================================
# MAINS STATES
# =============================================================================
MAINS_STATE_OK = 0
MAINS_STATE_FAIL = 1
MAINS_STATE_RESTORE_WAIT = 2
MAINS_STATE_RETURN_DELAY = 3
MAINS_STATE_TRANSFER_TO_GENSET = 4
MAINS_STATE_TRANSFER_TO_MAINS = 5

# =============================================================================
# BATTERY STATES
# =============================================================================
BATTERY_STATE_NORMAL = 0
BATTERY_STATE_LOW = 1
BATTERY_STATE_CRITICAL = 2
BATTERY_STATE_DISCONNECTED = 3
BATTERY_STATE_CHARGING = 4

# =============================================================================
# START SOURCE
# =============================================================================
START_SOURCE_NONE = 0
START_SOURCE_MANUAL = 1
START_SOURCE_ATS_MAINS_FAIL = 2
START_SOURCE_REMOTE = 3
START_SOURCE_SCHEDULE = 4
START_SOURCE_LOAD_DEMAND = 5
START_SOURCE_TEST = 6

# =============================================================================
# RUNNING TYPE
# =============================================================================
RUNNING_TYPE_NO_LOAD = 0
RUNNING_TYPE_ON_LOAD = 1
RUNNING_TYPE_TEST = 2
RUNNING_TYPE_MAINTENANCE = 3

# =============================================================================
# ALERT CATEGORIES
# From DK_Serbian.c SENDER configuration strings (indices 7-10 and 37-39)
# =============================================================================
ALERT_CATEGORY_SHUTDOWN = "shutDown"
ALERT_CATEGORY_LOADDUMP = "loadDump"
ALERT_CATEGORY_WARNING = "warning"
ALERT_CATEGORY_NOT_USED = "notUsed"

# SENDER flag[2] values (ASCII characters in binary protocol)
# Based on packet analysis: flag[2] stores ASCII char '3', '4', '5', '6'
ALERT_FLAG_WARNING = ord('3')    # 0x33 = 51
ALERT_FLAG_NOT_USED = ord('4')   # 0x34 = 52
ALERT_FLAG_SHUTDOWN = ord('5')   # 0x35 = 53
ALERT_FLAG_LOADDUMP = ord('6')   # 0x36 = 54

ALERT_CATEGORY_MAP = {
    ord('3'): ALERT_CATEGORY_WARNING,
    ord('4'): ALERT_CATEGORY_NOT_USED,
    ord('5'): ALERT_CATEGORY_SHUTDOWN,
    ord('6'): ALERT_CATEGORY_LOADDUMP,
    # Legacy byte values (if protocol changes)
    3: ALERT_CATEGORY_WARNING,
    4: ALERT_CATEGORY_NOT_USED,
    5: ALERT_CATEGORY_SHUTDOWN,
    6: ALERT_CATEGORY_LOADDUMP,
}

# =============================================================================
# ALARM MESSAGES
# From DK_Serbian.c alarm string table (indices 48-255)
# Partial list of most common alarms
# =============================================================================
# Loaded from language files

# =============================================================================
# SENDER MESSAGE INDICATORS (flag[1])
# =============================================================================
SENDER_FLAG_HAS_MESSAGE = 0x01      # Active message present
SENDER_FLAG_CONFIGURED = 0x03       # Configured but no message
SENDER_FLAG_INACTIVE = 0x7F         # Slot inactive/unused

# =============================================================================
# OUTPUT FUNCTIONS
# From DK_Serbian.c output function strings (indices 0-199+)
# =============================================================================
# Loaded from language files

# =============================================================================
# PROTOCOL OFFSETS
# =============================================================================
class Offsets:
    """Binary protocol field offsets"""
    HEADER = 0                  # 8 bytes: "DY0DD500"
    PROTOCOL_INFO = 8           # 8 bytes
    MODBUS_PORT = 18            # 2 bytes (big-endian)
    UNIQUE_ID = 21              # 12 bytes (hex string)
    LAN_IP = 37                 # 4 bytes
    GENERATOR_NAME = 56         # 32 bytes (ASCII, null-padded)
    RUNTIME_MINUTES = 99        # 2 bytes (little-endian)
    MODE = 103                  # 1 byte (0/1/3/4)
    STATE = 105                 # 1 byte (0-31+)
    
    # Electrical measurements
    GENSET_L1_V = 181           # 2 bytes, /10
    GENSET_L2_V = 185           # 2 bytes, /10
    GENSET_L3_V = 189           # 2 bytes, /10
    GENSET_I1_A = 193           # 2 bytes, /10
    GENSET_I2_A = 197           # 2 bytes, /10
    GENSET_I3_A = 201           # 2 bytes, /10
    GENSET_L1_L2_V = 205        # 2 bytes, /10
    GENSET_L2_L3_V = 209        # 2 bytes, /10
    GENSET_L3_L1_V = 213        # 2 bytes, /10
    GENSET_P_TOTAL_KW = 217     # 2 bytes, /10
    GENSET_S_TOTAL_KVA = 225    # 2 bytes, /10
    GENSET_FREQ_HZ = 231        # 2 bytes, /100
    ENGINE_RPM = 237            # 2 bytes
    BATTERY_VOLTAGE_VDC = 239   # 2 bytes, /100
    OIL_PRESSURE_BAR = 243      # 2 bytes, /10
    COOLANT_TEMP_C = 245        # 2 bytes, /10
    FUEL_LEVEL_PERCENT = 247    # 2 bytes, /10
    
    # SENDER slots and alerts
    SENDER_SLOTS_START = 258    # 8 slots × 19 bytes
    SENDER_SLOT_SIZE = 19       # 16 bytes name + 3 bytes flags
    ALERT_MESSAGES_START = 413  # 20 bytes per message, pipe-terminated
    
    # Statistics
    GENSET_STARTS_COUNT = 503   # 2 bytes
    REACTIVE_ENERGY_IND = 507   # 4 bytes, /10
    ENGINE_RUN_HOURS = 511      # 2 bytes, /100
    HOURS_TO_SERVICE_1 = 515    # 2 bytes, /100
    DAYS_TO_SERVICE_1 = 519     # 4 bytes, /100
    TOTAL_KWH = 539             # 4 bytes, /10
    GENSET_CRANKS_COUNT = 543   # 2 bytes
    REACTIVE_ENERGY_CAP = 547   # 2 bytes, /10
    
    # Network
    MAC_ADDRESS = 592           # 6 bytes


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def get_mode_name(mode_code: int) -> str:
    """Get human-readable mode name"""
    return MODE_NAMES.get(mode_code, f"Unknown Mode ({mode_code})")


def get_state_name(state_code: int) -> str:
    """Get human-readable genset state name"""
    return STATE_NAMES.get(state_code, f"Unknown State ({state_code})")


def get_engine_state_name(engine_state_code: int) -> str:
    """Get human-readable engine state name"""
    return ENGINE_STATE_NAMES.get(engine_state_code, f"Unknown Engine State ({engine_state_code})")


def get_breaker_state_name(breaker_state_code: int) -> str:
    """Get human-readable breaker state name"""
    return BREAKER_STATE_NAMES.get(breaker_state_code, f"Unknown Breaker State ({breaker_state_code})")


def get_mains_state_name(mains_state_code: int) -> str:
    """Get human-readable mains state name"""
    return MAINS_STATE_NAMES.get(mains_state_code, f"Unknown Mains State ({mains_state_code})")


def get_battery_state_name(battery_state_code: int) -> str:
    """Get human-readable battery state name"""
    return BATTERY_STATE_NAMES.get(battery_state_code, f"Unknown Battery State ({battery_state_code})")


def get_start_source_name(start_source_code: int) -> str:
    """Get human-readable start source name"""
    return START_SOURCE_NAMES.get(start_source_code, f"Unknown Start Source ({start_source_code})")


def get_running_type_name(running_type_code: int) -> str:
    """Get human-readable running type name"""
    return RUNNING_TYPE_NAMES.get(running_type_code, f"Unknown Running Type ({running_type_code})")


def get_alert_category(flag2_value: int) -> str:
    """Get alert category from SENDER flag[2]"""
    return ALERT_CATEGORY_MAP.get(flag2_value, ALERT_CATEGORY_NOT_USED)


def get_alarm_name(alarm_index: int) -> str:
    """Get alarm message name by index"""
    return ALARM_MESSAGES.get(alarm_index, f"Alarm #{alarm_index}")
