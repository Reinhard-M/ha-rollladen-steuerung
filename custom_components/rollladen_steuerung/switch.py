# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Reinhard-M. Unofficial community integration, not affiliated with Home Assistant.
"""Switches: lock-out protection, shading, automation blocked."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity

from .const import SWITCHES
from .entity import SettingEntity

ICONS = {
    "lockout": "mdi:door-closed-lock",
    "shading_enabled": "mdi:blinds-horizontal",
    "hide_times": "mdi:eye-off-outline",
    "auto_hold": "mdi:hand-back-right",
}


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    c = entry.runtime_data
    async_add_entities(SettingSwitch(c, entry, key) for key in SWITCHES if c.has_key(key))


class SettingSwitch(SettingEntity, SwitchEntity):
    _attr_entity_category = None

    def __init__(self, controller, entry, key: str) -> None:
        super().__init__(controller, entry, key)
        self._attr_icon = ICONS.get(key)

    @property
    def is_on(self) -> bool:
        return bool(self.controller.settings[self._key])

    def _parse_restored(self, state: str):
        return state == "on" if state in ("on", "off") else None

    async def async_turn_on(self, **kwargs) -> None:
        self._apply(True)

    async def async_turn_off(self, **kwargs) -> None:
        self._apply(False)
