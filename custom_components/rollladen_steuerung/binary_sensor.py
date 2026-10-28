# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Reinhard-M. Unofficial community integration, not affiliated with Home Assistant.
"""Binary sensor: shading active."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity

from .entity import SteuerungEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    async_add_entities([ShadingBinarySensor(entry.runtime_data, entry)])


class ShadingBinarySensor(SteuerungEntity, BinarySensorEntity):
    _attr_icon = "mdi:blinds-horizontal"

    def __init__(self, controller, entry) -> None:
        super().__init__(controller, entry, "shading")

    @property
    def is_on(self) -> bool:
        return self.controller.shading
