# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Reinhard-M. Unofficial community integration, not affiliated with Home Assistant.
"""Rollladen Steuerung: automation for shutters, blinds and awnings (day/night, shading, lock-out protection)."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType

try:
    from homeassistant.components.frontend import add_extra_js_url
except ImportError:  # pragma: no cover
    add_extra_js_url = None

from .const import DOMAIN
from .controller import Controller
from .entity_refs import async_resolve_stored, async_track_renames, async_update_issue, issue_id

_LOGGER = logging.getLogger(__name__)

CARD_FILE = Path(__file__).parent / "frontend" / "rollladen-steuerung-card.js"
CARD_URL = f"/{DOMAIN}/rollladen-steuerung-card.js"
CARD_KEY = f"{DOMAIN}_card_registered"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type RollladenSteuerungConfigEntry = ConfigEntry[Controller]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    await _async_register_card(hass)
    return True


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the card and load it in the frontend (once per Home Assistant instance)."""
    if hass.data.get(CARD_KEY):
        return
    http = getattr(hass, "http", None)
    if http is None:
        _LOGGER.warning("HTTP nicht verfügbar, Lovelace-Karte wird (noch) nicht registriert")
        return
    try:
        from homeassistant.components.http import StaticPathConfig

        await http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(CARD_FILE), cache_headers=False)]
        )
        mtime = await hass.async_add_executor_job(os.path.getmtime, CARD_FILE)
    except Exception:  # noqa: BLE001 - the card is optional
        _LOGGER.exception("Lovelace-Karte konnte nicht bereitgestellt werden")
        return
    hass.data[CARD_KEY] = True
    url = f"{CARD_URL}?v={int(mtime)}"
    if await _async_register_resource(hass, url):
        return
    if add_extra_js_url is not None:
        try:
            add_extra_js_url(hass, url)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Lovelace-Karte konnte nicht ins Frontend eingetragen werden")


async def _async_register_resource(hass: HomeAssistant, url: str) -> bool:
    """Register the card as a dashboard resource or update it (Lovelace in storage mode)."""
    try:
        try:
            from homeassistant.components.lovelace.const import LOVELACE_DATA

            data = hass.data.get(LOVELACE_DATA)
        except ImportError:
            data = hass.data.get("lovelace")
        if data is None or getattr(data, "resource_mode", None) != "storage":
            return False
        resources = data.resources
        if not getattr(resources, "loaded", True):
            await resources.async_load()
            resources.loaded = True
        for item in resources.async_items():
            if item["url"].split("?")[0] == CARD_URL:
                if item["url"] != url:
                    await resources.async_update_item(item["id"], {"res_type": "module", "url": url})
                return True
        await resources.async_create_item({"res_type": "module", "url": url})
        return True
    except Exception:  # noqa: BLE001 - fall back to add_extra_js_url
        _LOGGER.warning("Dashboard-Ressource konnte nicht eingetragen werden", exc_info=True)
        return False


async def async_setup_entry(hass: HomeAssistant, entry: RollladenSteuerungConfigEntry) -> bool:
    await _async_register_card(hass)  # fallback in case async_setup ran too early
    # Entities renamed while this entry was not loaded: follow them via their registry id
    async_resolve_stored(hass, entry)
    controller = Controller(hass, entry)
    entry.runtime_data = controller
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _remove_stale_entities(hass, entry, controller)
    # start only after the settings have been restored
    await controller.async_start()
    if controller.reset_lockout:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, "device_type_applied": controller.device_type}
        )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    # Renames while loaded are taken over into the options; missing entities -> Repairs issue
    async_track_renames(hass, entry)

    @callback
    def _check_references(_hass: HomeAssistant | None = None) -> None:
        async_update_issue(hass, entry)
        controller.notify()

    entry.async_on_unload(async_at_started(hass, _check_references))
    return True


def _remove_stale_entities(hass: HomeAssistant, entry, controller: Controller) -> None:
    """Remove entities that no longer exist in the current configuration."""
    reg = er.async_get(hass)
    for ent in er.async_entries_for_config_entry(reg, entry.entry_id):
        key = ent.translation_key
        if key and not controller.has_key(key):
            reg.async_remove(ent.entity_id)


async def _async_update_listener(hass: HomeAssistant, entry: RollladenSteuerungConfigEntry) -> None:
    if dict(entry.options) != entry.runtime_data.opt:  # reload only when the options changed
        await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: RollladenSteuerungConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_stop()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: RollladenSteuerungConfigEntry) -> None:
    ir.async_delete_issue(hass, DOMAIN, issue_id(entry))
