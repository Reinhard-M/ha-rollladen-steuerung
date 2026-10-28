# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Reinhard-M. Unofficial community integration, not affiliated with Home Assistant.
"""Diagnostics: state and position."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import DEGREE, LIGHT_LUX, PERCENTAGE, UnitOfTemperature

from homeassistant.const import EntityCategory

from .controller import INPUT_SENSORS
from .entity import SteuerungEntity

STATES = ["unknown", "night", "day", "shading", "shading_ending"]


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    c = entry.runtime_data
    entities: list = [
        StateSensor(c, entry),
        DiagnosticSensor(c, entry),
        DelaySensor(c, entry),
        LastCommandSensor(c, entry),
    ]
    entities += [InputSensor(c, entry, key) for key in INPUT_SENSORS if c.has_key(key)]
    async_add_entities(entities)


class StateSensor(SteuerungEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATES

    def __init__(self, controller, entry) -> None:
        super().__init__(controller, entry, "state")

    @property
    def native_value(self) -> str:
        return self.controller.phase

    @property
    def icon(self) -> str:
        return {
            "night": "mdi:weather-night",
            "shading": "mdi:blinds-horizontal",
            "shading_ending": "mdi:timer-sand",
        }.get(self.controller.phase, "mdi:weather-sunny")

    @property
    def extra_state_attributes(self) -> dict:
        c = self.controller
        return {
            "conditions": c.last_conditions,
            "blocked": c.blocked,
            "hold": c.hold,
            "device_type": c.device_type,
            "contact": c.read_contact(),
            "cover_state": (c.hass.states.get(c.cover).state if c.hass.states.get(c.cover) else None),
            "previous_position": c.pre_pos,
        }


class DiagnosticSensor(SteuerungEntity, SensorEntity):
    """All input values currently delivered, as attributes (for debugging)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:bug-outline"

    def __init__(self, controller, entry) -> None:
        super().__init__(controller, entry, "diagnostics")

    @property
    def native_value(self) -> str:
        if gone := self.controller.missing_entities():
            return ("Konfigurationsfehler, Entität fehlt: " + ", ".join(gone))[:255]
        missing = self.controller.missing_inputs()
        return ("Eingang fehlt: " + ", ".join(missing))[:255] if missing else "ok"

    @property
    def extra_state_attributes(self) -> dict:
        return self.controller.diagnostics()


INPUT_META = {
    "input_brightness": (SensorDeviceClass.ILLUMINANCE, LIGHT_LUX),
    "input_outdoor": (SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS),
    "input_indoor": (SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS),
    "input_elevation": (None, DEGREE),
    "input_azimuth": (None, DEGREE),
}


class InputSensor(SteuerungEntity, SensorEntity):
    """Mirrors the value the controller reads from the respective input (diagnostics)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, controller, entry, key: str) -> None:
        super().__init__(controller, entry, key)
        self._input = key
        dev, unit = INPUT_META.get(key, (None, None))
        self._attr_device_class = dev
        self._attr_native_unit_of_measurement = unit
        if unit is not None:
            self._attr_state_class = SensorStateClass.MEASUREMENT
        if key == "input_day":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = ["day", "night"]
        elif key == "input_block":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = ["blocked", "free"]
        elif key == "input_contact":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = ["open", "tilted", "closed"]

    @property
    def native_value(self):
        return self.controller.input_value(self._input)

    @property
    def extra_state_attributes(self) -> dict:
        eid = self.controller.opt.get(INPUT_SENSORS[self._input])
        st = self.controller.hass.states.get(eid) if eid else None
        return {"quelle": eid, "rohwert": st.state if st else None}


class DelaySensor(SteuerungEntity, SensorEntity):
    """Shows delayed or held-back drives (diagnostics)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:timer-sand"

    def __init__(self, controller, entry) -> None:
        super().__init__(controller, entry, "delay_status")

    @property
    def native_value(self) -> str:
        return self.controller.delay_status()[0][:255]

    @property
    def extra_state_attributes(self) -> dict:
        return {"faellig_um": self.controller.delay_status()[1]}


class LastCommandSensor(SteuerungEntity, SensorEntity):
    """Last command sent to the shutter with its trigger; attribute: the last 12 commands."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:script-text-outline"

    def __init__(self, controller, entry) -> None:
        super().__init__(controller, entry, "last_command")

    @property
    def native_value(self) -> str | None:
        return (self.controller.last_action or "")[:255] or None

    @property
    def extra_state_attributes(self) -> dict:
        return {"protokoll": list(self.controller.action_log)}
