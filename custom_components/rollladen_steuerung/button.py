# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Reinhard-M. Unofficial community integration, not affiliated with Home Assistant.
"""Buttons Up, Down, Stop, MyPosition, Back (manual control and calibration)."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity

from .const import BUTTONS, CMD_BACK, CMD_DOWN, CMD_MYPOS, CMD_STOP, CMD_UP
from .entity import SteuerungEntity

ICONS = {
    CMD_UP: "mdi:arrow-up",
    CMD_DOWN: "mdi:arrow-down",
    CMD_STOP: "mdi:stop",
    CMD_MYPOS: "mdi:star-circle-outline",
    CMD_BACK: "mdi:undo-variant",
}


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    c = entry.runtime_data
    async_add_entities(
        CommandButton(c, entry, key) for key in BUTTONS if c.has_key(f"button_{key}")
    )


class CommandButton(SteuerungEntity, ButtonEntity):
    def __init__(self, controller, entry, key: str) -> None:
        super().__init__(controller, entry, f"button_{key}")
        self._cmd = key
        self._attr_icon = ICONS[key]

    async def async_press(self) -> None:
        await self.controller.async_command(self._cmd)
