"""Entity references: follow renames, report missing entities (Repairs), fallback drive."""
import pytest
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.rollladen_steuerung.entity_refs import DATA_REGISTRY_IDS, issue_id
from custom_components.rollladen_steuerung.repairs import MissingEntitiesFlow

from .test_steuerung import DOMAIN, setup


@pytest.fixture(autouse=True)
def _auto(enable_custom_integrations):
    yield


def _register_button(hass, object_id: str) -> str:
    reg = er.async_get(hass)
    ent = reg.async_get_or_create("button", "jarolift", f"uid_{object_id}", suggested_object_id=object_id)
    hass.states.async_set(ent.entity_id, "unknown")
    return ent.entity_id


async def _rename(hass, old: str, new: str) -> None:
    er.async_get(hass).async_update_entity(old, new_entity_id=new)
    hass.states.async_remove(old)
    hass.states.async_set(new, "unknown")
    await hass.async_block_till_done()


def _issue(hass, entry):
    return ir.async_get(hass).async_get_issue(DOMAIN, issue_id(entry))


async def test_rename_while_loaded_updates_options(hass, freezer):
    old = _register_button(hass, "jarolift_schlafz_l_shade")
    e = await setup(hass, freezer, shade_entity=old)
    entry = e.c.entry
    assert DATA_REGISTRY_IDS in entry.data

    await _rename(hass, old, "button.schlafz_l_shade")
    assert entry.options["shade_entity"] == "button.schlafz_l_shade"
    assert entry.runtime_data.opt["shade_entity"] == "button.schlafz_l_shade"  # reloaded
    assert _issue(hass, entry) is None


async def test_rename_while_not_loaded_is_repaired_at_setup(hass, freezer):
    old = _register_button(hass, "jarolift_kuche_shade")
    e = await setup(hass, freezer, shade_entity=old)
    entry = e.c.entry
    assert await hass.config_entries.async_unload(entry.entry_id)
    await _rename(hass, old, "button.kuche_shade")
    assert entry.options["shade_entity"] == old  # not loaded: nothing followed yet

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.options["shade_entity"] == "button.kuche_shade"


async def test_missing_entity_creates_issue_and_fix_flow_repairs(hass, freezer):
    e = await setup(hass, freezer, shade_entity="button.gibt_es_nicht")
    entry = e.c.entry
    issue = _issue(hass, entry)
    assert issue is not None and issue.is_fixable
    assert issue.translation_placeholders["entities"] == "button.gibt_es_nicht"
    diag = hass.states.get(e.ids["diagnostics"])
    assert diag.state.startswith("Konfigurationsfehler") and "button.gibt_es_nicht" in diag.state

    flow = MissingEntitiesFlow(entry.entry_id)
    flow.hass = hass
    result = await flow.async_step_init()
    assert result["type"] == "form" and "shade_entity" in result["data_schema"].schema
    result = await flow.async_step_init({"shade_entity": "button.mypos"})
    await hass.async_block_till_done()
    assert result["type"] == "form" and result["step_id"] == "done"
    assert result["description_placeholders"]["title"] == entry.title
    assert "button.gibt_es_nicht → button.mypos" in result["description_placeholders"]["changes"]
    assert result["description_placeholders"]["hint"] == ""
    result = await flow.async_step_done({})
    assert result["type"] == "create_entry"
    assert entry.options["shade_entity"] == "button.mypos"
    assert _issue(hass, entry) is None
    assert hass.states.get(e.ids["diagnostics"]).state == "ok"


async def test_fix_flow_nothing_missing_names_instance_and_unavailable(hass, freezer):
    """Entity came back (only 'unavailable'): no bare 'problem fixed', but a clear abort."""
    e = await setup(hass, freezer, shade_entity="button.gibt_es_nicht")
    entry = e.c.entry
    hass.states.async_set("button.gibt_es_nicht", "unavailable")
    await hass.async_block_till_done()
    flow = MissingEntitiesFlow(entry.entry_id)
    flow.hass = hass
    result = await flow.async_step_init()
    assert result["type"] == "abort" and result["reason"] == "nothing_to_fix_unavailable"
    assert result["description_placeholders"]["title"] == entry.title
    assert "button.gibt_es_nicht" in result["description_placeholders"]["entities"]
    assert _issue(hass, entry) is None


async def test_fix_flow_empty_field_removes_input(hass, freezer):
    e = await setup(hass, freezer, shade_entity="button.gibt_es_nicht")
    entry = e.c.entry
    flow = MissingEntitiesFlow(entry.entry_id)
    flow.hass = hass
    result = await flow.async_step_init({})
    assert result["step_id"] == "done"
    await hass.async_block_till_done()
    assert "shade_entity" not in entry.options
    assert _issue(hass, entry) is None


async def test_registered_entity_without_state_is_not_missing(hass, freezer):
    """Integration of the button still starting: registered, no state yet -> no issue."""
    reg = er.async_get(hass)
    ent = reg.async_get_or_create("button", "jarolift", "uid_late", suggested_object_id="spaet")
    e = await setup(hass, freezer, shade_entity=ent.entity_id)
    assert _issue(hass, e.c.entry) is None


async def test_missing_mypos_button_falls_back_to_position(hass, freezer):
    """The case of 2026-10-28: window tilted, night via MyPosition, button renamed."""
    e = await setup(hass, freezer, shade_entity="button.jarolift_schlafz_l_shade")
    pressed = async_mock_service(hass, "button", "press")
    e.c.settings["night_tilted_mode"] = "mypos"
    hass.states.async_set("sensor.kontakt", "tilted")
    hass.states.async_set("input_boolean.tag", "off")
    await hass.async_block_till_done()
    assert not pressed
    assert e.pos and e.pos[-1].data["position"] == 20  # night_tilted_pos instead of no drive
    assert "fehlt" in e.c.last_action or any("fehlt" in x for x in e.c.action_log)


async def test_fix_flow_disabled_entity_gives_reason_and_unchanged_hint(hass, freezer):
    reg = er.async_get(hass)
    ent = reg.async_get_or_create(
        "button", "mqtt", "uid_off", suggested_object_id="aus",
        disabled_by=er.RegistryEntryDisabler.INTEGRATION,
    )
    e = await setup(hass, freezer, shade_entity=ent.entity_id)
    entry = e.c.entry
    flow = MissingEntitiesFlow(entry.entry_id)
    flow.hass = hass
    result = await flow.async_step_init()
    assert result["type"] == "form"
    assert "disabled" in result["description_placeholders"]["entities"]  # English (test default)
    hass.config.language = "de"
    result = await flow.async_step_init()
    assert "deaktiviert" in result["description_placeholders"]["entities"]
    result = await flow.async_step_init({"shade_entity": ent.entity_id})  # same entity again
    assert result["step_id"] == "done"
    assert "unverändert" in result["description_placeholders"]["changes"]
    assert "Hinweis" in result["description_placeholders"]["hint"]
