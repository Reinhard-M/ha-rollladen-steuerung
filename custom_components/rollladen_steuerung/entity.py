# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Reinhard-M. Unofficial community integration, not affiliated with Home Assistant.
"""Base classes of the entities."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, docs_url
from .controller import Controller


class SteuerungEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, controller: Controller, entry: ConfigEntry, key: str) -> None:
        self.controller = controller
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            entry_type=DeviceEntryType.SERVICE,
            # Shown as "Visit service" link on the device page -> README
            configuration_url=docs_url(controller.hass.config.language),
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self.controller.signal, self._refresh)
        )

    @callback
    def _refresh(self) -> None:
        self.async_write_ha_state()


class SettingEntity(SteuerungEntity, RestoreEntity):
    """The value lives in controller.settings[key]; it is restored after a restart."""

    _attr_entity_category = EntityCategory.CONFIG

    def _parse_restored(self, state: str):
        raise NotImplementedError

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state not in ("unknown", "unavailable"):
            try:
                value = self._parse_restored(last.state)
            except (ValueError, TypeError):
                value = None
            if value is not None and not (self._key == "lockout" and self.controller.reset_lockout):
                self.controller.settings[self._key] = value

    @callback
    def _apply(self, value) -> None:
        self.controller.set_setting(self._key, value)
        self.controller.notify()
