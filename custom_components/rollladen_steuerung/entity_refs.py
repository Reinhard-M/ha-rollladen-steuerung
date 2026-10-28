# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Reinhard-M. Unofficial community integration, not affiliated with Home Assistant.
"""Keep the entity references in the options valid.

The options store plain entity_ids (readable, shown as-is in the options dialog). Renaming an
entity ("Recreate entity ID" / changing the entity_id) does not touch config entries of other
integrations, so a reference would silently point to nothing. This module

* follows renames live (entity registry "update" events with ``old_entity_id``),
* remembers the registry id (UUID) of every referenced entity in ``entry.data`` and uses it at
  setup to repair references renamed while the entry was not loaded,
* reports references that cannot be resolved as a Repairs issue (with a fix flow).
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir

from .const import (
    CONF_AZIMUTH,
    CONF_BLOCK,
    CONF_BRIGHTNESS,
    CONF_CONTACT,
    CONF_COVER,
    CONF_DAY,
    CONF_DAYNIGHT,
    CONF_ELEVATION,
    CONF_EVENING,
    CONF_EXTERNAL,
    CONF_INDOOR,
    CONF_MORNING,
    CONF_OUTDOOR,
    CONF_SHADE_ENTITY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# All option keys that hold an entity_id
ENTITY_KEYS: tuple[str, ...] = (
    CONF_COVER,
    CONF_DAY,
    CONF_DAYNIGHT,
    CONF_SHADE_ENTITY,
    CONF_CONTACT,
    CONF_BRIGHTNESS,
    CONF_OUTDOOR,
    CONF_INDOOR,
    CONF_ELEVATION,
    CONF_AZIMUTH,
    CONF_EXTERNAL,
    CONF_BLOCK,
    CONF_MORNING,
    CONF_EVENING,
)
DATA_REGISTRY_IDS = "registry_ids"  # entry.data: option key -> entity registry id (UUID)


def issue_id(entry: ConfigEntry) -> str:
    return f"missing_entities_{entry.entry_id}"


def referenced(options: dict[str, Any]) -> dict[str, str]:
    """Option key -> entity_id for every configured entity reference."""
    return {k: v for k in ENTITY_KEYS if isinstance(v := options.get(k), str) and v}


def is_missing(hass: HomeAssistant, entity_id: str) -> bool:
    """True if the entity does not exist (or is disabled).

    An entity that is registered but has no state yet (integration still starting) does not
    count as missing; an entity without registry entry counts as missing only without a state.
    """
    entry = er.async_get(hass).async_get(entity_id)
    if entry is not None:
        return entry.disabled_by is not None
    return hass.states.get(entity_id) is None


def missing(hass: HomeAssistant, options: dict[str, Any]) -> dict[str, str]:
    """Option key -> entity_id of every reference that cannot be resolved."""
    return {k: eid for k, eid in referenced(options).items() if is_missing(hass, eid)}


@callback
def async_resolve_stored(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """At setup: repair renamed references via the stored registry ids, then refresh the ids."""
    reg = er.async_get(hass)
    stored: dict[str, str] = dict(entry.data.get(DATA_REGISTRY_IDS) or {})
    options = dict(entry.options)
    changed = False
    for key, eid in referenced(options).items():
        if reg.async_get(eid) is not None or key not in stored:
            continue
        new = er.async_resolve_entity_id(reg, stored[key])
        if new and new != eid:
            _LOGGER.info("%s: %s wurde umbenannt in %s, Verweis angepasst", entry.title, eid, new)
            options[key] = new
            changed = True

    ids: dict[str, str] = {}
    for key, eid in referenced(options).items():
        if (reg_entry := reg.async_get(eid)) is not None:
            ids[key] = reg_entry.id
        elif key in stored:  # keep the id: the entity may come back (e.g. integration not loaded)
            ids[key] = stored[key]
    if changed or ids != stored:
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, DATA_REGISTRY_IDS: ids},
            options=options if changed else entry.options,
        )


@callback
def async_track_renames(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Follow renames and removals of referenced entities while the entry is loaded."""

    @callback
    def _on_registry_updated(event: Event) -> None:
        action = event.data.get("action")
        if action == "update" and (old := event.data.get("old_entity_id")):
            new = event.data["entity_id"]
            options = dict(entry.options)
            keys = [k for k, v in referenced(options).items() if v == old]
            if not keys:
                return
            for key in keys:
                options[key] = new
            _LOGGER.info(
                "%s: %s wurde umbenannt in %s, Verweis angepasst (%s)",
                entry.title, old, new, ", ".join(keys),
            )
            # The update listener reloads the entry with the new entity_ids
            hass.config_entries.async_update_entry(entry, options=options)
            return
        if action in ("create", "remove", "update") and event.data.get("entity_id") in referenced(
            dict(entry.options)
        ).values():
            async_update_issue(hass, entry)
            if (controller := getattr(entry, "runtime_data", None)) is not None:
                controller.notify()  # diagnostic sensor shows the new state

    entry.async_on_unload(
        hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, _on_registry_updated)
    )


@callback
def async_update_issue(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, str]:
    """Create or delete the Repairs issue for unresolvable references; returns them."""
    gone = missing(hass, dict(entry.options))
    if not gone:
        ir.async_delete_issue(hass, DOMAIN, issue_id(entry))
        return gone
    if hass.state is not CoreState.running:
        return gone  # other integrations may still be loading; checked again once started
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id(entry),
        is_fixable=True,
        is_persistent=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="missing_entities",
        translation_placeholders={
            "title": entry.title,
            "entities": ", ".join(sorted(set(gone.values()))),
        },
        data={"entry_id": entry.entry_id},
    )
    return gone
