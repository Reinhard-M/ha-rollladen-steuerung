# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Reinhard-M. Unofficial community integration, not affiliated with Home Assistant.
"""Control logic of one shutter/blind/awning instance.

Overview
--------
One ``Controller`` exists per config entry (= per shutter). It

* watches the input entities (day/night, window contact, sun, weather, external command),
* decides *automatic* drives (night, shading, lock-out catch-up, ...) from those events,
* sends the drive commands to the cover (optionally delayed, see ``auto_delay``),
* estimates the position itself if the cover has no position feedback (``PositionTracker``),
* offers a small calibration wizard for that estimate.

Position convention everywhere: 0 % = closed (awning: extended), 100 % = open (awning: retracted).
Manual drives (buttons, external command, card) never pause the automation; the automation only
reacts to *events*, it never polls the position.
"""
from __future__ import annotations

import logging
import re
from collections import deque
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    AWNING_HIDDEN,
    AWNING_NIGHT_POS,
    AWNING_SHADE_POS,
    CMD_POSITION,
    POSITION_PATTERN,
    CAL_DOWN,
    CAL_MYPOS,
    CAL_OFF,
    CAL_STEPS,
    CAL_TARGET,
    CAL_UP,
    CMD_BACK,
    CMD_DOWN,
    CMD_MYPOS,
    CMD_STOP,
    CMD_UP,
    CONF_AZIMUTH,
    CONF_BRIGHTNESS,
    CONF_CONTACT,
    CONF_CONTACT_CLOSED,
    CONF_CONTACT_OPEN,
    CONF_CONTACT_TILTED,
    CONF_COMBINED_CHANNEL,
    CONF_COMBINED_DEVICE,
    CONF_COVER,
    CONF_DAY,
    CONF_DAYNIGHT,
    CONF_DEVICE_TYPE,
    CONF_ELEVATION,
    CONF_EVENING,
    CONF_BLOCK,
    CONF_EXTERNAL,
    CONF_INDOOR,
    CONF_MORNING,
    CONF_OUTDOOR,
    CONF_POSITION_SOURCE,
    CONF_SHADE_ENTITY,
    CONF_USE_TILT,
    DEFAULT_COMBINED_CHANNEL,
    DEFAULT_CONTACT_CLOSED,
    DEFAULT_CONTACT_OPEN,
    DEFAULT_CONTACT_TILTED,
    DOMAIN,
    END_PREVIOUS,
    EXTERNAL_MAP,
    HIDE_KEYS,
    LEGACY_KEYS,
    MODE_MYPOS,
    MODE_POSITION,
    MYPOS_KEYS,
    NUMBERS,
    POS_INTERNAL,
    SELECTS,
    SHADE_MYPOS,
    SLAT_KEYS,
    SWITCHES,
    TIME_KEYS,
    TYPE_AWNING,
    TYPE_DOOR,
    TYPE_WINDOW,
)

_LOGGER = logging.getLogger(__name__)

DAY_VALUES = {"on", "day", "tag", "true"}
NIGHT_VALUES = {"off", "night", "nacht", "false"}

# Night drive settings per contact state: (mode key, position key)
SLAT_NIGHT = {"open": "slat_night_open", "tilted": "slat_night_tilted", "closed": "slat_night_closed"}
NIGHT_KEYS = {
    "open": ("night_open_mode", "night_open_pos"),
    "tilted": ("night_tilted_mode", "night_tilted_pos"),
    "closed": ("night_closed_mode", "night_closed_pos"),
}

# Diagnostic sensors for the delivered input values: key -> config field
INPUT_SENSORS = {
    "input_day": CONF_DAY,
    "input_contact": CONF_CONTACT,
    "input_brightness": CONF_BRIGHTNESS,
    "input_outdoor": CONF_OUTDOOR,
    "input_indoor": CONF_INDOOR,
    "input_elevation": CONF_ELEVATION,
    "input_azimuth": CONF_AZIMUTH,
    "input_external": CONF_EXTERNAL,
    "input_block": CONF_BLOCK,
    "input_morning": CONF_MORNING,
    "input_evening": CONF_EVENING,
}


# ---------------------------------------------------------------------- Position estimation
def _advance(p: float, direction: int, elapsed: float, t: dict[str, float]) -> float:
    """Position after `elapsed` seconds of travel (0 = closed, 100 = open); t = run times for 100 %."""
    if direction < 0:
        return max(0.0, p - 100 / t["down"] * elapsed)
    return min(100.0, p + 100 / t["up"] * elapsed)


def travel_time(p_from: float, p_to: float, t: dict[str, float]) -> float:
    """Travel time in seconds from p_from to p_to."""
    if p_to < p_from:
        return (p_from - p_to) / 100 * t["down"]
    return (p_to - p_from) / 100 * t["up"]


class PositionTracker:
    """Estimates the position (0 = closed, 100 = open) from direction and run times."""

    def __init__(self) -> None:
        self.pos = 100.0
        self._dir = 0
        self._t0 = 0.0
        self._p0 = 100.0
        self._times: dict[str, float] = {}

    @staticmethod
    def _now() -> float:
        return dt_util.utcnow().timestamp()

    @property
    def direction(self) -> int:
        return self._dir

    def current(self) -> float:
        if self._dir == 0:
            return self.pos
        p = _advance(self._p0, self._dir, self._now() - self._t0, self._times)
        return max(0.0, min(100.0, p))

    def start(self, direction: int, times: dict[str, float]) -> None:
        self.pos = self.current()
        self._p0 = self.pos
        self._dir = direction
        self._times = dict(times)
        self._t0 = self._now()

    def stop(self) -> None:
        self.pos = self.current()
        self._dir = 0

    def set(self, pos: float) -> None:
        self.pos = max(0.0, min(100.0, float(pos)))
        self._dir = 0


def in_azimuth_range(value: float, start: float, end: float) -> bool:
    """Azimuth within start..end, also across north (start > end)."""
    if value != 360:
        value %= 360
    if start == end:
        return True
    if start <= end:
        return start <= value <= end
    return value >= start or value <= end


class Controller:
    """One instance per shutter."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.opt: dict[str, Any] = dict(entry.options)
        self.signal = f"{DOMAIN}_{entry.entry_id}_update"

        self.settings: dict[str, Any] = {k: v[0] for k, v in NUMBERS.items()}
        self.settings.update({k: v[1] for k, v in SELECTS.items()})
        self.settings.update(SWITCHES)
        self.device_type = self.opt.get(CONF_DEVICE_TYPE, TYPE_WINDOW)
        self.settings["lockout"] = self.device_type == TYPE_DOOR
        if self.is_awning:
            self.settings["shade_pos"] = AWNING_SHADE_POS  # default: fully extended
        # Device type newly chosen -> apply the lock-out default again (do not restore the old one)
        self.reset_lockout = entry.data.get("device_type_applied") != self.device_type

        self.tracker = PositionTracker()
        self.is_day: bool | None = None
        self.shading = False
        self.shading_ending = False
        self.blocked = False  # automatic drive held back by the lock-out protection
        self.held_back = False  # automatic drive held back because the automation is blocked
        self.pre_pos: float = 100.0
        self.last_auto: dict[str, dict[str, Any]] = {}
        self.last_conditions: dict[str, bool | None] = {}
        self.last_external: str | None = None
        self.slat_value: float | None = None
        self.last_action: str | None = None
        self.action_log: deque[str] = deque(maxlen=12)
        self.calibration = CAL_OFF  # current calibration step
        self._cal_start: float | None = None
        self._cal_moving = False  # saw a movement report (opening/closing) of the device
        self._cal_cancel: Callable[[], None] | None = None

        self._reason = "Start"
        self._cmd_ts = 0.0
        self._contact: str | None = None
        self._end_due: float | None = None
        self._catchup_due: float | None = None
        self._auto_due: float | None = None
        self._auto_cancel: Callable[[], None] | None = None
        self._stop_target: float | None = None
        self._end_cancel: Callable[[], None] | None = None
        self._catchup_cancel: Callable[[], None] | None = None
        self._stop_cancel: Callable[[], None] | None = None
        self._unsubs: list[Callable[[], None]] = []

    # ------------------------------------------------------------------ Helpers
    @property
    def cover(self) -> str:
        return self.opt[CONF_COVER]

    @property
    def internal(self) -> bool:
        return self.opt.get(CONF_POSITION_SOURCE) == POS_INTERNAL

    @property
    def is_awning(self) -> bool:
        return self.opt.get(CONF_DEVICE_TYPE) == TYPE_AWNING

    @property
    def hold(self) -> bool:
        """Automation blocked (switch; follows the input "External block")."""
        return bool(self.settings["auto_hold"])

    @property
    def use_tilt(self) -> bool:
        return bool(self.opt.get(CONF_USE_TILT)) and not self.is_awning

    @property
    def has_mypos(self) -> bool:
        """Is there a MyPosition button on the device?"""
        return bool(self.opt.get(CONF_SHADE_ENTITY))

    @property
    def combined(self) -> bool:
        """Send height and slats in ONE command (Homematic COMBINED_PARAMETER)?"""
        return bool(self.opt.get(CONF_COMBINED_DEVICE)) and self.use_tilt and not self.internal

    async def _send_combined(self, pos: float, slat: float) -> None:
        pos = max(0, min(100, round(float(pos))))
        slat = max(0, min(100, round(float(slat))))
        await self._call(
            "homematicip_local",
            "put_paramset",
            {
                "device_id": self.opt[CONF_COMBINED_DEVICE],
                "channel": int(self.opt.get(CONF_COMBINED_CHANNEL) or DEFAULT_COMBINED_CHANNEL),
                "paramset_key": "VALUES",
                "paramset": {"COMBINED_PARAMETER": f"L={pos},L2={slat}"},
                "retry": True,
            },
        )

    @property
    def lock_active(self) -> bool:
        return bool(self.settings["lockout"])

    def has_key(self, key: str) -> bool:
        """Does this setting/entity exist in this configuration?"""
        if key in LEGACY_KEYS:
            return False
        if self.is_awning and key in AWNING_HIDDEN:
            return False
        if key in INPUT_SENSORS:
            return bool(
                self.opt.get(INPUT_SENSORS[key])
                or (key == "input_day" and self.opt.get(CONF_DAYNIGHT))
            )
        if key in TIME_KEYS or key in ("calibration", "hide_times"):
            return self.internal
        if key == "mypos_pos":
            return self.internal and self.has_mypos
        if key in SLAT_KEYS or key == "target_slat":
            return self.use_tilt
        if key in MYPOS_KEYS or key == "button_mypos":
            return self.has_mypos
        return True

    @callback
    def notify(self) -> None:
        async_dispatcher_send(self.hass, self.signal)

    def set_setting(self, key: str, value: Any) -> None:
        was_hold = self.hold
        self.settings[key] = value
        if key == "shading_enabled":
            self.hass.async_create_task(self._evaluate_shading())
        elif key == "hide_times":
            self.hass.async_create_task(self.async_apply_hidden())
        elif key == "auto_hold":
            self.hass.async_create_task(self._update_hold(was_hold))

    async def async_apply_hidden(self) -> None:
        """Hide or show the run-time/calibration settings in the entity registry."""
        reg = er.async_get(self.hass)
        hide = bool(self.settings["hide_times"]) and self.internal
        for ent in er.async_entries_for_config_entry(reg, self.entry.entry_id):
            if ent.translation_key not in HIDE_KEYS:
                continue
            if hide and ent.hidden_by is None:
                reg.async_update_entity(ent.entity_id, hidden_by=er.RegistryEntryHider.INTEGRATION)
            elif not hide and ent.hidden_by == er.RegistryEntryHider.INTEGRATION:
                reg.async_update_entity(ent.entity_id, hidden_by=None)

    def _mode(self, key: str) -> str:
        """Target kind of a setting; MyPosition only with a MyPosition button."""
        mode = self.settings[key]
        return MODE_MYPOS if mode == MODE_MYPOS and self.has_mypos else MODE_POSITION

    def _times(self) -> dict[str, float]:
        s = self.settings
        return {
            "down": max(float(s["time_down"]), 0.1),
            "up": max(float(s["time_up"]), 0.1),
        }

    def _state(self, entity_id: str | None):
        if not entity_id:
            return None
        st = self.hass.states.get(entity_id)
        if st is None or st.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        return st

    def _float(self, entity_id: str | None, attr: str | None = None) -> float | None:
        st = self._state(entity_id)
        if st is None:
            return None
        value = st.attributes.get(attr) if attr else st.state
        if value is None and attr is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _sun_value(self, entity_id: str | None, attr: str) -> float | None:
        if entity_id and entity_id.startswith("sun."):
            return self._float(entity_id, attr)
        return self._float(entity_id)

    def _read_day(self) -> bool | None:
        st = self._state(self.opt.get(CONF_DAY) or self.opt.get(CONF_DAYNIGHT))
        if st is None:
            return None
        value = st.state.strip().lower()
        if value in DAY_VALUES:
            return True
        if value in NIGHT_VALUES:
            return False
        return None

    def read_contact(self) -> str | None:
        st = self._state(self.opt.get(CONF_CONTACT))
        if st is None:
            return None
        value = st.state.strip().lower()
        for name, key, default in (
            ("open", CONF_CONTACT_OPEN, DEFAULT_CONTACT_OPEN),
            ("tilted", CONF_CONTACT_TILTED, DEFAULT_CONTACT_TILTED),
            ("closed", CONF_CONTACT_CLOSED, DEFAULT_CONTACT_CLOSED),
        ):
            words = {w.strip().lower() for w in str(self.opt.get(key) or default).split(",")}
            if value in words:
                return name
        return None

    def current_position(self) -> float | None:
        if self.internal:
            return round(self.tracker.current(), 1)
        st = self.hass.states.get(self.cover)
        if st is None:
            return None
        try:
            return float(st.attributes["current_position"])
        except (KeyError, TypeError, ValueError):
            return None

    # ------------------------------------------------------------------ Start/stop
    async def async_start(self) -> None:
        self.is_day = self._read_day()
        self._contact = self.read_contact()
        o = self.opt

        def watch(keys: list[str], cb: Callable[[Event], None]) -> None:
            ids = [o[k] for k in keys if o.get(k)]
            if ids:
                self._unsubs.append(async_track_state_change_event(self.hass, ids, cb))

        watch([CONF_DAY, CONF_DAYNIGHT], self._on_day_event)
        watch([CONF_EXTERNAL], self._on_external_event)
        if o.get(CONF_BLOCK):  # the input defines the switch (at startup and on every change)
            self.settings["auto_hold"] = self._read_block(bool(self.settings["auto_hold"]))
        watch([CONF_BLOCK], self._on_block_event)
        watch([CONF_MORNING, CONF_EVENING], self._on_time_event)
        watch([CONF_CONTACT], self._on_contact_event)
        watch(
            [CONF_BRIGHTNESS, CONF_OUTDOOR, CONF_INDOOR, CONF_ELEVATION, CONF_AZIMUTH],
            self._on_input_event,
        )
        watch([CONF_COVER], self._on_cover_event)
        await self.async_apply_hidden()
        self.notify()  # show the switch state after taking over the input

    async def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        for cancel in ("_end_cancel", "_catchup_cancel", "_stop_cancel", "_cal_cancel", "_auto_cancel"):
            fn = getattr(self, cancel)
            if fn:
                fn()
                setattr(self, cancel, None)

    def _cancel_end_timer(self) -> None:
        self._end_due = None
        if self._end_cancel:
            self._end_cancel()
            self._end_cancel = None
        self.shading_ending = False

    def _cancel_catchup(self) -> None:
        self._catchup_due = None
        if self._catchup_cancel:
            self._catchup_cancel()
            self._catchup_cancel = None

    def _cancel_stop_timer(self) -> None:
        if self._stop_cancel:
            self._stop_cancel()
            self._stop_cancel = None

    # ------------------------------------------------------------------ Events
    @callback
    def _on_day_event(self, _event: Event) -> None:
        self.hass.async_create_task(self._handle_day())

    @callback
    def _on_contact_event(self, _event: Event) -> None:
        self.hass.async_create_task(self._handle_contact())

    @callback
    def _on_input_event(self, _event: Event) -> None:
        self.hass.async_create_task(self._evaluate_shading())

    @callback
    def _on_time_event(self, _event: Event) -> None:
        self.notify()  # display only (drive times)

    @callback
    def _on_external_event(self, event: Event) -> None:
        new = event.data.get("new_state")
        if new is None or new.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        cmd, value = self.parse_external(new.state)
        self.last_external = new.state
        if cmd:
            self.hass.async_create_task(self.async_command(cmd, value))
        self.notify()

    def _read_block(self, default: bool = False) -> bool:
        """Input "External block": on/true/1 = automation blocked (unclear state = unchanged)."""
        eid = self.opt.get(CONF_BLOCK)
        st = self._state(eid) if eid else None
        if st is None or st.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return default
        return st.state.strip().lower() in ("on", "true", "1", "yes", "ja", "an")

    @callback
    def _on_block_event(self, _event: Event) -> None:
        self.hass.async_create_task(self._block_changed())

    async def _block_changed(self) -> None:
        was = self.hold
        self.settings["auto_hold"] = self._read_block(was)  # the switch follows the input
        self._reason = "Extern blockieren"
        await self._update_hold(was)

    @staticmethod
    def parse_external(state: str) -> tuple[str | None, float | None]:
        """State of the external sensor -> (command, value). A number or "position:40" = position."""
        text = state.strip().lower()
        if text in EXTERNAL_MAP:
            return EXTERNAL_MAP[text], None
        m = re.match(POSITION_PATTERN, text)
        if m:
            return CMD_POSITION, max(0.0, min(100.0, float(m.group(1).replace(",", "."))))
        return None, None

    @callback
    def _on_cover_event(self, event: Event) -> None:
        new = event.data.get("new_state")
        old = event.data.get("old_state")
        if new is None:
            return
        # Calibration: start/end follow the movement reports of the device (without the latency of
        # the button press and reaction time); if they are missing, button press and stop count
        if self._cal_start is not None and old is not None:
            now = dt_util.utcnow().timestamp()
            if new.state in ("opening", "closing") and not self._cal_moving:
                self._cal_start, self._cal_moving = now, True
            elif self._cal_moving and old.state in ("opening", "closing") and new.state in (
                "open", "closed", "stopped"
            ):
                self._finish_calibration_step(now - self._cal_start)
                return
        if not self.internal:
            self.notify()  # position/slats of the device have changed
            return
        t = self.tracker
        # Feedback shortly after our own command is an echo (often late) and must not
        # restart the estimate
        own = dt_util.utcnow().timestamp() - self._cmd_ts < 3
        if new.state == "opening":
            if t.direction != 1 and not own:
                t.start(1, self._times())
        elif new.state == "closing":
            if t.direction != -1 and not own:
                t.start(-1, self._times())
        elif new.state == "closed":
            # Some devices report "closed" after a stop, even half way: only a running
            # downward drive without our own stop timer really ends at the bottom
            if t.direction == -1 and self._stop_cancel is None:
                t.set(0)
            elif t.direction != 0 and self._stop_cancel is None:
                t.stop()
        elif t.direction != 0 and self._stop_cancel is None and not own:
            # Device stands still (open/stopped) although we did not want to stop: arrived at the top or stopped externally
            if new.state == "open" and t.direction == 1 and t.current() > 90:
                t.set(100)
            else:
                t.stop()
        self.notify()

    async def _handle_day(self) -> None:
        new = self._read_day()
        if new is None or new == self.is_day:
            return
        old, self.is_day = self.is_day, new
        self._reason = "Wechsel auf Tag" if new else "Wechsel auf Nacht"
        self._cancel_end_timer()
        self._cancel_catchup()
        self._cancel_auto_timer()
        self.shading = False
        self.blocked = False
        self._contact = self.read_contact()
        if old is None:  # first information after startup: do not drive
            self.notify()
            return
        if new:
            self.pre_pos = self._day_position_value()
            if self.settings["shading_enabled"] and all(
                v for v in self._conditions(False).values() if v is not None
            ):
                self.shading = True
        if new and self.is_awning and not self.shading:
            self.notify()  # awning: during the day it only extends for shading, nothing at day start
            return
        await self._apply_auto()
        self.notify()

    def _day_position_value(self) -> float:
        """Position the shutter drives to during the day (without shading)."""
        if self._mode("day_mode") == MODE_MYPOS:
            return float(self.settings["mypos_pos"]) if self.internal else 100.0
        return float(self.settings["day_pos"])

    async def _handle_contact(self) -> None:
        old, new = self._contact, self.read_contact()
        self._contact = new
        if new == old or self.is_day is None:
            return
        if self.is_awning:
            return  # awning: window contact has no effect
        self._reason = f"Kontakt {old} -> {new}"
        if self.blocked:
            # Held-back drive: only make it up when the contact is no longer "open"
            if new == "open":
                self._cancel_catchup()
            else:
                self._schedule_catchup()
        elif self.is_day is False:
            await self._apply_auto()  # night: height matching the contact
        # Day: window contacts have no effect
        self.notify()

    def _schedule_catchup(self) -> None:
        self._cancel_catchup()
        delay = float(self.settings["catchup_delay"])
        if delay <= 0:
            self.hass.async_create_task(self._catchup())
            return

        @callback
        def _fire(_now) -> None:
            self._catchup_cancel = None
            self._catchup_due = None
            self.hass.async_create_task(self._catchup())

        self._catchup_due = dt_util.utcnow().timestamp() + delay
        self._catchup_cancel = async_call_later(self.hass, delay, _fire)

    async def _catchup(self) -> None:
        """Make up the held-back automatic drive: currently valid target, not the old one."""
        if not self.blocked:
            return
        self._reason = "Nachholen"
        self.blocked = False
        await self._apply_auto()
        self.notify()

    # ------------------------------------------------------------------ Automatic drives
    def _target_now(self) -> dict[str, Any] | None:
        """Currently valid target of the automation (only night values at night, shading only by day)."""
        s = self.settings
        if self.is_day is None:
            return None
        if not self.is_day and self.is_awning:
            return {"phase": "night", "mode": MODE_POSITION, "pos": float(AWNING_NIGHT_POS), "slat": 0.0}
        if not self.is_day:
            contact = self.read_contact() or "closed"
            mode_key, pos_key = NIGHT_KEYS[contact]
            return {
                "phase": "night", "mode": self._mode(mode_key),
                "pos": float(s[pos_key]), "slat": float(s[SLAT_NIGHT[contact]]),
            }
        if self.shading:
            mode = MODE_MYPOS if s["shade_mode"] == SHADE_MYPOS and self.has_mypos else MODE_POSITION
            return {"phase": "day", "mode": mode, "pos": float(s["shade_pos"]),
                    "slat": float(s["slat_shade"])}
        return {"phase": "day", "mode": self._mode("day_mode"),
                "pos": float(s["day_pos"]), "slat": float(s["slat_day"])}

    def _is_up(self) -> bool:
        pos = self.current_position()
        return pos is None or pos >= 99

    def _locked_out(self) -> bool:
        """Lock-out protection: only if the shutter is up and the contact reports "open"."""
        return self.lock_active and self.read_contact() == "open" and self._is_up()

    def _cancel_auto_timer(self) -> None:
        self._auto_due = None
        if self._auto_cancel:
            self._auto_cancel()
            self._auto_cancel = None

    async def _apply_auto(self, target: dict[str, Any] | None = None) -> None:
        """Automatic drive, delayed by *automatic drive delay* (automation only, never manual)."""
        t = target or self._target_now()
        if t is None:
            return
        if self.hold:
            # Automation blocked: remember the drive, make it up on release to the then valid target
            self._cancel_auto_timer()
            self.held_back = True
            self.notify()
            return
        if self._locked_out():
            self._cancel_auto_timer()
            self.blocked = True
            self.notify()
            return
        self.blocked = False
        delay = float(self.settings["auto_delay"])
        self._cancel_auto_timer()  # a new target replaces one that is still waiting
        if delay <= 0:
            await self._drive_target(t)
            self.notify()
            return

        @callback
        def _fire(_now) -> None:
            self._auto_cancel = None
            self._auto_due = None
            self.hass.async_create_task(self._send_delayed(t))

        self._auto_due = dt_util.utcnow().timestamp() + delay
        self._auto_cancel = async_call_later(self.hass, delay, _fire)
        self.notify()

    async def _send_delayed(self, t: dict[str, Any]) -> None:
        if self.hold:
            self.held_back = True
            self.notify()
            return
        if self._locked_out():  # the contact changed during the waiting time
            self.blocked = True
            self.notify()
            return
        self.blocked = False
        await self._drive_target(t)
        self.notify()

    async def _drive_target(self, t: dict[str, Any]) -> None:
        self.last_auto[t["phase"]] = dict(t)
        if t["mode"] == MODE_MYPOS:
            await self.drive_mypos()
            await self._set_tilt(t["slat"])
        elif self.combined:
            await self._send_combined(t["pos"], t["slat"])  # one command instead of height + slats separately
            self.slat_value = float(t["slat"])
        else:
            await self.drive_pos(t["pos"])
            await self._set_tilt(t["slat"])

    # ------------------------------------------------------------------ Shading
    def _conditions(self, active: bool) -> dict[str, bool | None]:
        """Individual conditions; None = not configured (counts as fulfilled)."""
        s, o = self.settings, self.opt
        c: dict[str, bool | None] = {}

        def threshold(key: str, name: str, thr: float) -> None:
            if not o.get(key):
                c[name] = None
                return
            v = self._float(o[key])
            c[name] = v is not None and v >= thr

        if o.get(CONF_ELEVATION):
            v = self._sun_value(o[CONF_ELEVATION], "elevation")
            c["elevation"] = v is not None and v >= s["shade_elevation_min"]
        else:
            c["elevation"] = None
        if o.get(CONF_AZIMUTH):
            v = self._sun_value(o[CONF_AZIMUTH], "azimuth")
            c["azimuth"] = v is not None and in_azimuth_range(
                v, s["shade_azimuth_from"], s["shade_azimuth_to"]
            )
        else:
            c["azimuth"] = None
        threshold(CONF_OUTDOOR, "outdoor_temp", s["shade_outdoor_temp"])
        threshold(CONF_INDOOR, "indoor_temp", s["shade_indoor_temp"])
        threshold(
            CONF_BRIGHTNESS,
            "brightness",
            s["shade_brightness_end"] if active else s["shade_brightness_start"],
        )
        self.last_conditions = c
        return c

    async def _evaluate_shading(self) -> None:
        if self.is_day is not True:
            self.notify()
            return
        if not self.settings["shading_enabled"]:
            if self.shading:
                await self._end_shading()
            self.notify()
            return
        ok = all(v for v in self._conditions(self.shading).values() if v is not None)
        if not self.shading:
            if ok:
                self._reason = "Beschattung Start"
                self.pre_pos = self._pre_position()
                self.shading = True
                await self._apply_auto()
        elif ok:
            self._cancel_end_timer()
        elif self._end_cancel is None:
            delay = float(self.settings["shade_end_delay"])
            if delay <= 0:
                await self._end_shading()
            else:
                self.shading_ending = True

                @callback
                def _fire(_now) -> None:
                    self._end_cancel = None
                    self.hass.async_create_task(self._end_shading())

                self._end_due = dt_util.utcnow().timestamp() + delay
                self._end_cancel = async_call_later(self.hass, delay, _fire)
        self.notify()

    def _pre_position(self) -> float:
        pos = self.current_position()
        return 100.0 if pos is None else float(pos)

    async def _end_shading(self) -> None:
        self._cancel_end_timer()
        self.shading = False
        self._reason = "Ende der Beschattung"
        target = self._target_now()
        if target and self.settings["shade_end"] == END_PREVIOUS:
            target = {**target, "mode": MODE_POSITION, "pos": 100.0 if self.pre_pos >= 99 else self.pre_pos}
        await self._apply_auto(target)
        self.notify()

    # ------------------------------------------------------------------ Commands
    async def _call(self, domain: str, service: str, data: dict[str, Any]) -> None:
        extra = ", ".join(f"{k}={v}" for k, v in data.items() if k != "entity_id")
        if domain == "cover":
            self._cmd_ts = dt_util.utcnow().timestamp()
        self.last_action = (
            f"{dt_util.now().strftime('%H:%M:%S')} {self._reason}: {domain}.{service} {extra}".strip()
        )
        self.action_log.appendleft(self.last_action)
        try:
            await self.hass.services.async_call(domain, service, data, blocking=True)
        except HomeAssistantError as err:
            _LOGGER.warning("%s.%s fehlgeschlagen: %s", domain, service, err)

    async def drive_up(self) -> None:
        self._cancel_stop_timer()
        await self._call("cover", "open_cover", {"entity_id": self.cover})
        if self.internal:
            self.tracker.start(1, self._times())
        self.notify()

    async def drive_down(self) -> None:
        self._cancel_stop_timer()
        await self._call("cover", "close_cover", {"entity_id": self.cover})
        if self.internal:
            self.tracker.start(-1, self._times())
        self.notify()

    async def drive_stop(self) -> None:
        self._cancel_stop_timer()
        await self._call("cover", "stop_cover", {"entity_id": self.cover})
        if self.internal:
            self.tracker.stop()
        self.notify()

    async def drive_pos(self, pos: float) -> None:
        pos = max(0.0, min(100.0, float(pos)))
        if not self.internal:
            await self._call(
                "cover", "set_cover_position", {"entity_id": self.cover, "position": round(pos)}
            )
            return
        await self._internal_move(pos)

    async def drive_mypos(self) -> None:
        """Drive to the motor's MyPosition (button on the device)."""
        entity = self.opt.get(CONF_SHADE_ENTITY)
        if not entity:
            _LOGGER.warning("MyPosition angefordert, aber kein MyPosition-Taster konfiguriert")
            return
        self._cancel_stop_timer()
        await self._press(entity)
        if self.internal:
            self._track_to(float(self.settings["mypos_pos"]))
        self.notify()

    def _track_to(self, target: float) -> None:
        """Track the position while driving to MyPosition (the motor stops by itself)."""
        t = self.tracker
        cur = t.current()
        if abs(target - cur) < 1:
            t.set(target)
            return
        times = self._times()
        t.start(1 if target > cur else -1, times)
        self._stop_target = target

        @callback
        def _arrived(_now) -> None:
            self._stop_cancel = None
            self.tracker.set(target)
            self.notify()

        self._stop_cancel = async_call_later(self.hass, travel_time(cur, target, times), _arrived)

    async def _internal_move(self, target: float) -> None:
        """Position drive without position feedback: direction + run time + stop."""
        t = self.tracker
        if target >= 99.5:
            await self.drive_up()
            return
        if target <= 0.5:
            await self.drive_down()
            return
        cur = t.current()
        if abs(target - cur) < 1:
            return
        self._cancel_stop_timer()
        times = self._times()
        duration = travel_time(cur, target, times)
        if target > cur:
            await self._call("cover", "open_cover", {"entity_id": self.cover})
            t.start(1, times)
        else:
            await self._call("cover", "close_cover", {"entity_id": self.cover})
            t.start(-1, times)
        self._stop_target = target

        @callback
        def _fire(_now) -> None:
            self._stop_cancel = None
            self.hass.async_create_task(self._timed_stop())

        self._stop_cancel = async_call_later(self.hass, duration, _fire)
        self.notify()

    async def _timed_stop(self) -> None:
        await self._call("cover", "stop_cover", {"entity_id": self.cover})
        self.tracker.set(self._stop_target if self._stop_target is not None else self.tracker.current())
        self.notify()

    async def _press(self, entity_id: str) -> None:
        domain = entity_id.split(".", 1)[0]
        if domain in ("button", "input_button"):
            await self._call(domain, "press", {"entity_id": entity_id})
        elif domain in ("switch", "input_boolean", "script", "scene", "light"):
            await self._call(domain, "turn_on", {"entity_id": entity_id})
        else:
            await self._call("homeassistant", "turn_on", {"entity_id": entity_id})

    async def _set_tilt(self, value: float) -> None:
        if self.use_tilt:
            await self._call(
                "cover",
                "set_cover_tilt_position",
                {"entity_id": self.cover, "tilt_position": round(value)},
            )

    def current_slat(self) -> float | None:
        st = self.hass.states.get(self.cover)
        if st is not None:
            try:
                return float(st.attributes["current_tilt_position"])
            except (KeyError, TypeError, ValueError):
                pass
        return self.slat_value

    async def async_set_position(self, value: float) -> None:
        """Manual position request (card/dashboard); the automation stays untouched."""
        self._reason = f"Manuell Position {round(value)}"
        slat = self.current_slat()
        if self.combined and slat is not None:
            await self._send_combined(value, slat)  # send the current slats along
            return
        await self.drive_pos(value)

    async def async_set_slat(self, value: float) -> None:
        self._reason = f"Manuell Lamellen {round(value)}"
        self.slat_value = float(value)
        pos = self.current_position()
        if self.combined and pos is not None:
            await self._send_combined(pos, value)  # send the current height along
        else:
            await self._set_tilt(value)
        self.notify()

    async def async_back(self) -> None:
        """After a manual drive back to the last automatically driven position of this time of day."""
        self._reason = "Zurück"
        phase = "night" if self.is_day is False else "day"
        target = self.last_auto.get(phase) or self._target_now()
        if target is None:
            return
        await self._drive_target(target)
        self.notify()

    async def _update_hold(self, was_hold: bool) -> None:
        """The block may have changed (switch or input); on release make up what was held back."""
        hold = self.hold
        if hold == was_hold:
            self.notify()
            return
        if hold:
            self._reason = "Automatik gesperrt"
            if self._auto_due is not None:  # a waiting (delayed) drive is made up later
                self.held_back = True
            self._cancel_auto_timer()
            self.notify()
            return
        self._reason = "Automatik freigegeben"
        if self.held_back:
            self.held_back = False
            await self._apply_auto()  # currently valid target (also under drive delay/lock-out)
        self.notify()

    async def async_command(self, cmd: str, value: float | None = None) -> None:
        """Manual/external commands (buttons, external sensor). The automation stays untouched."""
        if cmd == CMD_POSITION:
            if value is not None:
                await self.async_set_position(value)
            return
        self._reason = f"Kommando {cmd}"
        pressed = dt_util.utcnow().timestamp()
        if cmd == CMD_UP:
            await self.drive_up()
        elif cmd == CMD_DOWN:
            await self.drive_down()
        elif cmd == CMD_STOP:
            await self.drive_stop()
        elif cmd == CMD_MYPOS:
            await self.drive_mypos()
        elif cmd == CMD_BACK:
            await self.async_back()
            return
        else:
            return
        self._calibration_step(cmd, pressed)

    # ------------------------------------------------------------------ Calibration
    CAL_HINTS = {
        CAL_DOWN: "Rollo ganz oben. Runter (oder MyPosition) drücken, unten angekommen Stopp drücken.",
        CAL_UP: "Rollo ganz unten. Hoch (oder MyPosition) drücken, oben angekommen Stopp drücken.",
        CAL_MYPOS: "Rollo ganz oben. MyPosition drücken (Laufzeit runter muss gemessen sein). Meldet das Gerät opening/closing, endet die Messung von selbst, sonst Stopp drücken, sobald der Motor anhält.",
    }

    @property
    def calibration_steps(self) -> list[str]:
        """Available calibration steps (MyPosition only with a MyPosition button)."""
        return [x for x in CAL_STEPS if x != CAL_MYPOS or self.has_mypos]

    def set_calibration(self, step: str) -> None:
        self.calibration = step
        self._cal_start = None
        self._cal_moving = False
        self._cancel_cal_timer()
        self.notify()

    @property
    def calibration_hint(self) -> str | None:
        step = self.calibration
        if step == CAL_OFF:
            return None
        hint = self.CAL_HINTS[step]
        return f"{hint} (Messung läuft)" if self._cal_start is not None else hint

    def _calibration_step(self, cmd: str, pressed: float) -> None:
        step = self.calibration
        if step == CAL_OFF:
            return
        if self._cal_start is None:
            direction = {CAL_DOWN: CMD_DOWN, CAL_UP: CMD_UP}.get(step)
            if cmd == CMD_MYPOS or cmd == direction:
                self._cal_start = pressed
        elif cmd == CMD_STOP:
            if self._cal_moving:
                # the device reports the end itself; otherwise finish after 3 s with the stop time
                seconds = pressed - self._cal_start
                self._cancel_cal_timer()

                @callback
                def _fallback(_now) -> None:
                    self._cal_cancel = None
                    if self._cal_start is not None:
                        self._finish_calibration_step(seconds)

                self._cal_cancel = async_call_later(self.hass, 3, _fallback)
            else:
                self._finish_calibration_step(pressed - self._cal_start)
        self.notify()

    def _cancel_cal_timer(self) -> None:
        if self._cal_cancel:
            self._cal_cancel()
            self._cal_cancel = None

    def _finish_calibration_step(self, seconds: float) -> None:
        step, s = self.calibration, self.settings
        if step == CAL_MYPOS:
            # travel time from the top to MyPosition -> height from the measured run time down
            _d, lo, hi, *_ = NUMBERS["mypos_pos"]
            pos = 100 - 100 * seconds / max(float(s["time_down"]), 0.1)
            s["mypos_pos"] = round(max(lo, min(hi, pos)))
            self.tracker.set(s["mypos_pos"])
        else:
            key = CAL_TARGET[step]
            _d, lo, hi, *_ = NUMBERS[key]
            s[key] = round(max(lo, min(hi, seconds)), 1)
            # position at the end of the measuring drive
            self.tracker.set(0 if step == CAL_DOWN else 100)
        self._cancel_stop_timer()
        self._cancel_cal_timer()
        self._cal_start = None
        self._cal_moving = False
        steps = self.calibration_steps
        idx = steps.index(step) + 1
        self.calibration = steps[idx] if idx < len(steps) else CAL_OFF
        _LOGGER.debug("Kalibrierung %s: %.1f s", step, seconds)
        self.notify()

    # ------------------------------------------------------------------ State
    @property
    def phase(self) -> str:
        if self.is_day is None:
            return "unknown"
        if not self.is_day:
            return "night"
        if self.shading:
            return "shading_ending" if self.shading_ending else "shading"
        return "day"

    # ------------------------------------------------------------------ Diagnostics
    def diagnostics(self) -> dict[str, Any]:
        o = self.opt

        def raw(key: str) -> str | None:
            eid = o.get(key)
            if not eid:
                return None
            st = self.hass.states.get(eid)
            return f"{eid} = {st.state if st else 'nicht vorhanden'}"

        cover = self.hass.states.get(self.cover)
        data: dict[str, Any] = {
            "tag_quelle": raw(CONF_DAY) or raw(CONF_DAYNIGHT),
            "tag_erkannt": self.is_day,
            "kontakt": raw(CONF_CONTACT),
            "kontakt_erkannt": self.read_contact(),
            "helligkeit": raw(CONF_BRIGHTNESS),
            "aussentemperatur": raw(CONF_OUTDOOR),
            "zimmertemperatur": raw(CONF_INDOOR),
            "elevation": raw(CONF_ELEVATION),
            "azimuth": raw(CONF_AZIMUTH),
            "externer_eingang": raw(CONF_EXTERNAL),
            "extern_blockieren": raw(CONF_BLOCK),
            "fahrzeit_morgens": raw(CONF_MORNING),
            "fahrzeit_abends": raw(CONF_EVENING),
            "letztes_externes_kommando": self.last_external,
            "cover_zustand": cover.state if cover else "nicht vorhanden",
            "cover_position_gerät": cover.attributes.get("current_position") if cover else None,
            "position_verwendet": self.current_position(),
            "positionsquelle": "intern" if self.internal else "gerät",
            "gerätetyp": self.device_type,
            "bedingungen": self._conditions(self.shading),
            "beschattung": self.shading,
            "beschattung_endet": self.shading_ending,
            "vorherige_position": self.pre_pos,
            "zurückgehalten": self.blocked,
            "kalibrierung": self.calibration,
            "verzögerung": self.delay_status()[0],
            "letzter_befehl": self.last_action,
            "befehlsprotokoll": list(self.action_log),
        }
        return data

    def missing_inputs(self) -> list[str]:
        out = []
        for key in (CONF_DAY, CONF_BRIGHTNESS, CONF_OUTDOOR, CONF_INDOOR, CONF_ELEVATION,
                    CONF_AZIMUTH, CONF_CONTACT, CONF_COVER):
            eid = self.opt.get(key)
            if eid and self._state(eid) is None:
                out.append(eid)
        return out

    def delay_status(self) -> tuple[str, str | None]:
        """Text + due time (ISO) for delayed/held-back drives."""
        now = dt_util.utcnow().timestamp()
        parts: list[str] = []
        due: float | None = None
        if self._end_due is not None:
            parts.append(f"Beschattung endet in {max(0, round(self._end_due - now))} s")
            due = self._end_due
        if self._auto_due is not None:
            parts.append(f"Automatische Fahrt in {max(0, round(self._auto_due - now))} s")
            due = min(due, self._auto_due) if due else self._auto_due
        if self._catchup_due is not None:
            parts.append(f"Nachholen in {max(0, round(self._catchup_due - now))} s")
            due = min(due, self._catchup_due) if due else self._catchup_due
        if self.hold:
            parts.append(
                "Automatik gesperrt, Fahrt wartet auf Freigabe" if self.held_back else "Automatik gesperrt"
            )
        if self.blocked and self._catchup_due is None:
            parts.append("Fahrt zurückgehalten (Aussperrschutz, wartet auf Kontakt)")
        text = "; ".join(parts) if parts else "keine"
        return text, (dt_util.utc_from_timestamp(due).isoformat() if due else None)

    def input_value(self, key: str):
        """Current value of an input as read by the controller (None = not available)."""
        o = self.opt
        if key == "input_day":
            day = self._read_day()
            return None if day is None else ("day" if day else "night")
        if key == "input_contact":
            return self.read_contact()
        if key == "input_external":
            return self.last_external
        if key == "input_block":
            st = self._state(o.get(CONF_BLOCK))
            return None if st is None or st.state in (STATE_UNKNOWN, STATE_UNAVAILABLE) else (
                "blocked" if self._read_block() else "free"
            )
        if key == "input_elevation":
            return self._sun_value(o.get(CONF_ELEVATION), "elevation")
        if key == "input_azimuth":
            return self._sun_value(o.get(CONF_AZIMUTH), "azimuth")
        if key in ("input_morning", "input_evening"):
            st = self._state(o.get(INPUT_SENSORS[key]))
            return st.state if st else None
        return self._float(o.get(INPUT_SENSORS[key]))
