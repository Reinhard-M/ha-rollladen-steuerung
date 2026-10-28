# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Reinhard-M. Unofficial community integration, not affiliated with Home Assistant.
"""Select settings and calibration."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity

from .const import CAL_OFF, LEGACY_VALUES, SELECTS
from .entity import SettingEntity, SteuerungEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    c = entry.runtime_data
    entities: list = [SettingSelect(c, entry, key) for key in SELECTS if c.has_key(key)]
    if c.has_key("calibration"):
        entities.append(CalibrationSelect(c, entry))
    async_add_entities(entities)


class SettingSelect(SettingEntity, SelectEntity):
    def __init__(self, controller, entry, key: str) -> None:
        super().__init__(controller, entry, key)
        self._attr_options = list(SELECTS[key][0])

    @property
    def current_option(self) -> str:
        return self.controller.settings[self._key]

    def _parse_restored(self, state: str):
        state = LEGACY_VALUES.get(state, state)
        return state if state in self._attr_options else None

    async def async_select_option(self, option: str) -> None:
        self._apply(option)


class CalibrationSelect(SteuerungEntity, SelectEntity):
    _attr_icon = "mdi:tune-vertical"

    def __init__(self, controller, entry) -> None:
        super().__init__(controller, entry, "calibration")
        self._attr_options = [CAL_OFF, *controller.calibration_steps]

    @property
    def current_option(self) -> str:
        return self.controller.calibration

    @property
    def extra_state_attributes(self) -> dict:
        return {"hint": self.controller.calibration_hint}

    async def async_select_option(self, option: str) -> None:
        self.controller.set_calibration(option)
