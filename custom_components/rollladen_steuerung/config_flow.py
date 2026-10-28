# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Reinhard-M. Unofficial community integration, not affiliated with Home Assistant.
"""Config and options flow: choose the shutter (cover) and the input entities."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    DeviceSelector,
    DeviceSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    docs_url,
    CONF_AZIMUTH,
    CONF_BRIGHTNESS,
    CONF_CONTACT,
    CONF_CONTACT_CLOSED,
    CONF_CONTACT_OPEN,
    CONF_CONTACT_TILTED,
    CONF_COMBINED_CHANNEL,
    CONF_COMBINED_DEVICE,
    CONF_COVER,
    CONF_DAY,
    CONF_DEVICE_TYPE,
    CONF_EVENING,
    CONF_BLOCK,
    CONF_EXTERNAL,
    CONF_MORNING,
    CONF_ELEVATION,
    CONF_INDOOR,
    CONF_OUTDOOR,
    CONF_POSITION_SOURCE,
    CONF_SHADE_ENTITY,
    CONF_USE_TILT,
    DEFAULT_COMBINED_CHANNEL,
    DEFAULT_CONTACT_CLOSED,
    DEFAULT_CONTACT_OPEN,
    DEFAULT_CONTACT_TILTED,
    DEVICE_TYPES,
    DOMAIN,
    POS_DEVICE,
    POS_INTERNAL,
)

COVER_SUPPORT_POSITION = 4
COVER_SUPPORT_TILT_POSITION = 128

OPTIONAL_ENTITIES = [
    (CONF_BRIGHTNESS, ["sensor", "input_number"]),
    (CONF_OUTDOOR, ["sensor", "input_number"]),
    (CONF_INDOOR, ["sensor", "input_number"]),
    (CONF_ELEVATION, ["sensor", "sun", "input_number"]),
    (CONF_AZIMUTH, ["sensor", "sun", "input_number"]),
    (CONF_CONTACT, ["sensor", "select", "input_select", "binary_sensor", "input_boolean"]),
    (CONF_MORNING, ["sensor", "input_datetime", "time"]),
    (CONF_EVENING, ["sensor", "input_datetime", "time"]),
    (CONF_EXTERNAL, ["sensor", "input_text", "text", "select", "input_select"]),
    (CONF_BLOCK, ["binary_sensor", "input_boolean", "switch", "sensor"]),
    (CONF_SHADE_ENTITY, ["button", "input_button", "switch", "script", "scene", "input_boolean"]),
]


def _schema(hass, defaults: dict[str, Any], with_name: bool) -> vol.Schema:
    cover = defaults.get(CONF_COVER)
    features = 0
    if cover and (st := hass.states.get(cover)):
        features = int(st.attributes.get("supported_features", 0) or 0)
    default_source = POS_DEVICE if features & COVER_SUPPORT_POSITION else POS_INTERNAL
    default_tilt = bool(features & COVER_SUPPORT_TILT_POSITION)

    fields: dict[Any, Any] = {}
    if with_name:
        fields[vol.Required(CONF_NAME)] = TextSelector()
    fields[vol.Required(CONF_COVER, default=cover) if cover else vol.Required(CONF_COVER)] = (
        EntitySelector(EntitySelectorConfig(domain="cover"))
    )
    fields[
        vol.Required(CONF_DAY, default=defaults[CONF_DAY]) if defaults.get(CONF_DAY)
        else vol.Required(CONF_DAY)
    ] = EntitySelector(
        EntitySelectorConfig(
            domain=["binary_sensor", "sensor", "input_boolean", "switch", "input_select", "select"]
        )
    )
    fields[
        vol.Required(CONF_DEVICE_TYPE, default=defaults.get(CONF_DEVICE_TYPE, "window"))
    ] = SelectSelector(
        SelectSelectorConfig(
            options=DEVICE_TYPES,
            mode=SelectSelectorMode.DROPDOWN,
            translation_key="device_type",
        )
    )
    for key, domains in OPTIONAL_ENTITIES:
        suggested = defaults.get(key)
        if key in (CONF_ELEVATION, CONF_AZIMUTH) and key not in defaults and with_name:
            suggested = "sun.sun"
        fields[vol.Optional(key, description={"suggested_value": suggested})] = EntitySelector(
            EntitySelectorConfig(domain=domains)
        )
    fields[
        vol.Required(CONF_POSITION_SOURCE, default=defaults.get(CONF_POSITION_SOURCE, default_source))
    ] = SelectSelector(
        SelectSelectorConfig(
            options=[POS_DEVICE, POS_INTERNAL],
            mode=SelectSelectorMode.DROPDOWN,
            translation_key="position_source",
        )
    )
    fields[vol.Required(CONF_USE_TILT, default=defaults.get(CONF_USE_TILT, default_tilt))] = (
        BooleanSelector()
    )
    fields[
        vol.Optional(CONF_COMBINED_DEVICE, description={"suggested_value": defaults.get(CONF_COMBINED_DEVICE)})
    ] = DeviceSelector(DeviceSelectorConfig(integration="homematicip_local"))
    fields[vol.Optional(CONF_COMBINED_CHANNEL, default=defaults.get(CONF_COMBINED_CHANNEL, DEFAULT_COMBINED_CHANNEL))] = (
        NumberSelector(NumberSelectorConfig(min=0, max=99, step=1, mode=NumberSelectorMode.BOX))
    )
    for key, default in (
        (CONF_CONTACT_OPEN, DEFAULT_CONTACT_OPEN),
        (CONF_CONTACT_TILTED, DEFAULT_CONTACT_TILTED),
        (CONF_CONTACT_CLOSED, DEFAULT_CONTACT_CLOSED),
    ):
        fields[vol.Required(key, default=defaults.get(key, default))] = TextSelector()
    return vol.Schema(fields)


class RollladenSteuerungConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            options = dict(user_input)
            title = options.pop(CONF_NAME).strip()
            return self.async_create_entry(title=title, data={}, options=options)
        return self.async_show_form(
            step_id="user",
            data_schema=_schema(self.hass, {}, with_name=True),
            description_placeholders={"docs_url": docs_url(self.hass.config.language)},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return RollladenSteuerungOptionsFlow()


class RollladenSteuerungOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        defaults = dict(self.config_entry.options)
        defaults.setdefault(CONF_DAY, defaults.get("daynight_entity"))
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(self.hass, defaults, with_name=False),
            description_placeholders={"docs_url": docs_url(self.hass.config.language)},
        )
