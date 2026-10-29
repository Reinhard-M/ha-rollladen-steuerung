# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Reinhard-M. Unofficial community integration, not affiliated with Home Assistant.
"""Constants and the definition of all settings."""
from __future__ import annotations

DOMAIN = "rollladen_steuerung"

# Documentation (README) shown as a link in the config / options dialogs
DOCS_BASE = "https://github.com/Reinhard-M/ha-rollladen-steuerung"


def docs_url(language: str | None) -> str:
    """Return the README URL: German README for German UI, English README otherwise."""
    if language and language.lower().startswith("de"):
        return f"{DOCS_BASE}#readme"
    return f"{DOCS_BASE}/blob/main/README.en.md"

# ---- Configuration (config/options flow) ----
CONF_COVER = "cover"
CONF_DAY = "day_entity"
CONF_DAYNIGHT = "daynight_entity"  # deprecated, only read as a fallback
CONF_EXTERNAL = "external_entity"
CONF_BLOCK = "block_entity"  # binary input "External block" (true = automation blocked)
CONF_MORNING = "morning_entity"
CONF_EVENING = "evening_entity"
CONF_DEVICE_TYPE = "device_type"
CONF_BRIGHTNESS = "brightness_entity"
CONF_OUTDOOR = "outdoor_entity"
CONF_INDOOR = "indoor_entity"
CONF_ELEVATION = "elevation_entity"
CONF_AZIMUTH = "azimuth_entity"
CONF_CONTACT = "contact_entity"
CONF_SHADE_ENTITY = "shade_entity"
CONF_POSITION_SOURCE = "position_source"
CONF_USE_TILT = "use_tilt"
CONF_COMBINED_DEVICE = "combined_device"  # Homematic device: height + slats in one command
CONF_COMBINED_CHANNEL = "combined_channel"
DEFAULT_COMBINED_CHANNEL = 4
CONF_CONTACT_OPEN = "contact_open"
CONF_CONTACT_CLOSED = "contact_closed"
CONF_CONTACT_TILTED = "contact_tilted"

POS_DEVICE = "device"
POS_INTERNAL = "internal"

DEFAULT_CONTACT_OPEN = "open,on"
DEFAULT_CONTACT_CLOSED = "closed,off"
DEFAULT_CONTACT_TILTED = "tilted,tilt"

# ---- Target kinds ----
MODE_POSITION = "position"
MODE_MYPOS = "mypos"
TARGET_MODES = [MODE_POSITION, MODE_MYPOS]

TYPE_WINDOW = "window"
TYPE_DOOR = "door"
TYPE_AWNING = "awning"
DEVICE_TYPES = [TYPE_WINDOW, TYPE_DOOR, TYPE_AWNING]

SHADE_POSITION = "position"
SHADE_MYPOS = "mypos"
END_PREVIOUS = "previous"
END_UP = "up"

CMD_UP = "up"
CMD_DOWN = "down"
CMD_STOP = "stop"
CMD_MYPOS = "mypos"
CMD_BACK = "back"
CMD_POSITION = "position"  # drive to a position (value 0-100 in the state)

# Calibration: measuring drives (order = sequence)
CAL_OFF = "off"
CAL_DOWN = "down"  # shutter up -> all the way down
CAL_UP = "up"  # shutter down -> all the way up
CAL_MYPOS = "mypos"  # shutter up -> MyPosition (the motor stops by itself)
CAL_STEPS = [CAL_DOWN, CAL_UP, CAL_MYPOS]
CALIBRATIONS = [CAL_OFF, *CAL_STEPS]
# Calibration step -> setting that receives the measured time
CAL_TARGET = {CAL_DOWN: "time_down", CAL_UP: "time_up"}

# ---- Settings: key -> (default, min, max, step, unit, icon) ----
NUMBERS: dict[str, tuple] = {
    "day_pos": (100, 0, 100, 1, "%", "mdi:window-shutter-open"),
    "night_open_pos": (100, 0, 100, 1, "%", "mdi:window-shutter-open"),
    "night_closed_pos": (0, 0, 100, 1, "%", "mdi:window-shutter"),
    "night_tilted_pos": (20, 0, 100, 1, "%", "mdi:window-shutter-alert"),
    "shade_pos": (30, 0, 100, 1, "%", "mdi:blinds-horizontal"),
    "slat_night_open": (100, 0, 100, 1, "%", "mdi:blinds-horizontal"),
    "slat_night_closed": (0, 0, 100, 1, "%", "mdi:blinds-horizontal-closed"),
    "slat_night_tilted": (50, 0, 100, 1, "%", "mdi:blinds-horizontal"),
    "slat_shade": (50, 0, 100, 1, "%", "mdi:blinds-horizontal"),
    "slat_day": (100, 0, 100, 1, "%", "mdi:blinds-horizontal"),
    "shade_elevation_min": (10, -10, 90, 0.5, "°", "mdi:weather-sunny-alert"),
    "shade_azimuth_from": (90, 0, 360, 1, "°", "mdi:compass"),
    "shade_azimuth_to": (270, 0, 360, 1, "°", "mdi:compass"),
    "shade_outdoor_temp": (20, -30, 60, 0.5, "°C", "mdi:thermometer"),
    "shade_indoor_temp": (22, -10, 50, 0.5, "°C", "mdi:thermometer"),
    "shade_brightness_start": (30000, 0, 200000, 100, "lx", "mdi:brightness-7"),
    "shade_brightness_end": (20000, 0, 200000, 100, "lx", "mdi:brightness-5"),
    "shade_end_delay": (300, 0, 7200, 1, "s", "mdi:timer-sand"),
    "catchup_delay": (30, 0, 3600, 1, "s", "mdi:timer-sand"),
    "auto_delay": (0, 0, 600, 0.5, "s", "mdi:timer-outline"),
    # only with internal position:
    "mypos_pos": (50, 0, 100, 1, "%", "mdi:map-marker"),
    "time_down": (30, 0.5, 600, 0.1, "s", "mdi:arrow-collapse-down"),
    "time_up": (30, 0.5, 600, 0.1, "s", "mdi:arrow-collapse-up"),
}

# key -> (options, default)
SELECTS: dict[str, tuple[list[str], str]] = {
    "day_mode": (TARGET_MODES, MODE_POSITION),
    "night_open_mode": (TARGET_MODES, MODE_POSITION),
    "night_closed_mode": (TARGET_MODES, MODE_POSITION),
    "night_tilted_mode": (TARGET_MODES, MODE_POSITION),
    "shade_mode": ([SHADE_POSITION, SHADE_MYPOS], SHADE_POSITION),
    "shade_end": ([END_PREVIOUS, END_UP], END_PREVIOUS),
}
# Old stored values -> new values (restore after an update)
LEGACY_VALUES = {"shade": "mypos", "command": "mypos"}
# Selects without restore (action)
ACTION_SELECTS: dict[str, tuple[list[str], str]] = {
    "calibration": (CALIBRATIONS, CAL_OFF),
}

SWITCHES: dict[str, bool] = {
    "lockout": False,  # default: on for type "door" (see controller)
    "shading_enabled": True,
    "hide_times": False,
    "auto_hold": False,  # automation blocked (by hand; follows the input "External block")
}

# Only with internal position (calibration needed)
TIME_KEYS = ("time_down", "time_up")
# Hidden in the entity registry by the switch "Hide run times"
HIDE_KEYS = (*TIME_KEYS, "mypos_pos", "calibration")
# Omitted for awnings (night = retract; contact/slats/lock-out protection have no effect)
AWNING_HIDDEN = (
    "lockout", "night_open_pos", "night_closed_pos", "night_tilted_pos",
    "night_open_mode", "night_closed_mode", "night_tilted_mode",
    "slat_night_open", "slat_night_closed", "slat_night_tilted", "slat_shade", "slat_day",
    "target_slat",
)
AWNING_NIGHT_POS = 100  # retracted (like "shutter open")
AWNING_SHADE_POS = 0  # default extended (like "shutter closed")
# Only with slats enabled
SLAT_KEYS = ("slat_night_open", "slat_night_closed", "slat_night_tilted", "slat_shade", "slat_day")
# Only with a MyPosition button
MYPOS_KEYS = ("night_open_mode", "night_closed_mode", "night_tilted_mode", "day_mode", "shade_mode")
# Former keys that no longer exist (removed from the entity registry)
LEGACY_KEYS = (
    "button_shade", "shade_time_down", "shade_time_up", "position",
    "time_down_upper", "time_down_lower", "time_up_lower", "time_up_upper",
)
# External commands (values of the external sensor, case-insensitive)
EXTERNAL_MAP = {
    "up": CMD_UP, "hoch": CMD_UP,
    "down": CMD_DOWN, "runter": CMD_DOWN,
    "stop": CMD_STOP, "stopp": CMD_STOP,
    "mypos": CMD_MYPOS, "myposition": CMD_MYPOS, "my": CMD_MYPOS,
    "shade": CMD_MYPOS, "beschattung": CMD_MYPOS,
    "back": CMD_BACK, "zurueck": CMD_BACK, "zurück": CMD_BACK,
}
# Position command: "position:40", "position 40", "pos=40", "40", "40 %" (0-100)
POSITION_PATTERN = r"^(?:position|pos|h(?:ö|oe)he)?\s*[:=_ ]?\s*(-?\d+(?:[.,]\d+)?)\s*%?$"

BUTTONS = [CMD_UP, CMD_DOWN, CMD_STOP, CMD_MYPOS, CMD_BACK]

# Start lock: max. seconds commands wait after a HA start for cover / Homematic service
START_WAIT_MAX = 300
