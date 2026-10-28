# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Reinhard-M. Unofficial community integration, not affiliated with Home Assistant.
"""Number settings."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode

from .const import NUMBERS
from homeassistant.helpers.restore_state import RestoreEntity

from .entity import SettingEntity, SteuerungEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    c = entry.runtime_data
    entities: list = [SettingNumber(c, entry, key) for key in NUMBERS if c.has_key(key)]
    entities.append(TargetNumber(c, entry, "target_position"))
    if c.has_key("target_slat"):
        entities.append(TargetNumber(c, entry, "target_slat"))
    async_add_entities(entities)


class SettingNumber(SettingEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, controller, entry, key: str) -> None:
        super().__init__(controller, entry, key)
        _default, lo, hi, step, unit, icon = NUMBERS[key]
        self._attr_native_min_value = lo
        self._attr_native_max_value = hi
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon

    @property
    def native_value(self) -> float:
        return float(self.controller.settings[self._key])

    def _parse_restored(self, state: str):
        value = float(state)
        return value if self._attr_native_min_value <= value <= self._attr_native_max_value else None

    async def async_set_native_value(self, value: float) -> None:
        self._apply(round(float(value), 1))


class TargetNumber(SteuerungEntity, NumberEntity, RestoreEntity):
    """Manual control: shows the current position/slat position; setting it drives the shutter."""

    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "%"
    _attr_mode = NumberMode.BOX

    def __init__(self, controller, entry, key: str) -> None:
        super().__init__(controller, entry, key)
        self._attr_icon = "mdi:window-shutter" if key == "target_position" else "mdi:blinds-horizontal"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is None or last.state in ("unknown", "unavailable"):
            return
        try:
            value = float(last.state)
        except ValueError:
            return
        if self._key == "target_position" and self.controller.internal:
            self.controller.tracker.set(value)
        elif self._key == "target_slat":
            self.controller.slat_value = value

    @property
    def native_value(self) -> float | None:
        if self._key == "target_position":
            return self.controller.current_position()
        return self.controller.current_slat()

    async def async_set_native_value(self, value: float) -> None:
        if self._key == "target_position":
            await self.controller.async_set_position(value)
        else:
            await self.controller.async_set_slat(value)
