# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Reinhard-M. Unofficial community integration, not affiliated with Home Assistant.
"""Repairs fix flow: pick a replacement for entities the configuration points to but that no longer exist."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .config_flow import DAY_DOMAINS, OPTIONAL_ENTITIES
from .const import CONF_COVER, CONF_DAY, CONF_DAYNIGHT
from .entity_refs import async_update_issue, missing

DOMAINS: dict[str, list[str]] = {
    CONF_COVER: ["cover"],
    CONF_DAY: DAY_DOMAINS,
    CONF_DAYNIGHT: DAY_DOMAINS,
    **{key: domains for key, domains in OPTIONAL_ENTITIES},
}


class MissingEntitiesFlow(RepairsFlow):
    """Replace (or clear) every reference that cannot be resolved."""

    def __init__(self, entry_id: str) -> None:
        self.entry_id = entry_id

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        entry = self.hass.config_entries.async_get_entry(self.entry_id)
        if entry is None:
            return self.async_abort(reason="entry_removed")
        gone = missing(self.hass, dict(entry.options))
        if not gone:
            async_update_issue(self.hass, entry)
            return self.async_create_entry(data={})

        if user_input is not None:
            options = dict(entry.options)
            for key in gone:
                if user_input.get(key):
                    options[key] = user_input[key]
                elif key != CONF_COVER:
                    options.pop(key, None)  # left empty = input no longer used
            self.hass.config_entries.async_update_entry(entry, options=options)
            async_update_issue(self.hass, entry)
            return self.async_create_entry(data={})

        fields: dict[Any, Any] = {}
        for key in gone:
            marker = vol.Required(key) if key == CONF_COVER else vol.Optional(key)
            fields[marker] = EntitySelector(EntitySelectorConfig(domain=DOMAINS.get(key, [])))
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(fields),
            description_placeholders={
                "title": entry.title,
                "entities": "\n".join(f"- {eid}" for eid in gone.values()),
            },
        )


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None
) -> RepairsFlow:
    return MissingEntitiesFlow((data or {}).get("entry_id", ""))
