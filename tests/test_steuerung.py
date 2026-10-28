from datetime import timedelta

import pytest
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry, async_fire_time_changed, async_mock_service)

DOMAIN = "rollladen_steuerung"
COVER = "cover.test"


@pytest.fixture(autouse=True)
def _auto(enable_custom_integrations):
    yield


BASE = {
    "cover": COVER, "day_entity": "input_boolean.tag", "brightness_entity": "sensor.lux",
    "outdoor_entity": "sensor.aussen", "indoor_entity": "sensor.innen",
    "elevation_entity": "sensor.elev", "azimuth_entity": "sensor.azi",
    "contact_entity": "sensor.kontakt", "position_source": "device", "use_tilt": False,
    "contact_open": "open", "contact_tilted": "tilted", "contact_closed": "closed",
}


class Env:
    pass


async def setup(hass, freezer, **opts):
    hass.states.async_set("input_boolean.tag", "on")
    hass.states.async_set("sensor.lux", "0")
    hass.states.async_set("sensor.aussen", "10")
    hass.states.async_set("sensor.innen", "20")
    hass.states.async_set("sensor.elev", "0")
    hass.states.async_set("sensor.azi", "180")
    hass.states.async_set("sensor.kontakt", "closed")
    hass.states.async_set(COVER, "open", {"current_position": 100, "supported_features": 15})
    e = Env()
    e.open = async_mock_service(hass, "cover", "open_cover")
    e.close = async_mock_service(hass, "cover", "close_cover")
    e.stop = async_mock_service(hass, "cover", "stop_cover")
    e.pos = async_mock_service(hass, "cover", "set_cover_position")
    e.tilt = async_mock_service(hass, "cover", "set_cover_tilt_position")
    entry = MockConfigEntry(domain=DOMAIN, title="Test", data={}, options={**BASE, **opts})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    e.c = entry.runtime_data
    reg = er.async_get(hass)
    e.ids = {x.translation_key: x.entity_id for x in er.async_entries_for_config_entry(reg, entry.entry_id)}
    e.hass, e.freezer = hass, freezer
    return e


async def tick(e, seconds):
    e.freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(e.hass, dt_util.utcnow())
    await e.hass.async_block_till_done()


async def setv(e, entity, value, attrs=None):
    e.hass.states.async_set(entity, value, attrs)
    await e.hass.async_block_till_done()


def shading_inputs_ok(e):
    s = e.hass.states
    s.async_set("sensor.lux", "40000")
    s.async_set("sensor.aussen", "25")
    s.async_set("sensor.innen", "24")
    s.async_set("sensor.elev", "30")
    s.async_set("sensor.azi", "180")



def n_cmds(e):
    return len(e.pos) + len(e.open) + len(e.close)


async def test_night_targets_and_contact(hass, freezer):
    e = await setup(hass, freezer)
    assert e.c.phase == "day"
    await setv(e, "input_boolean.tag", "off")
    assert e.pos[-1].data["position"] == 0       # geschlossen -> Position 0
    await setv(e, "sensor.kontakt", "tilted")
    assert e.pos[-1].data["position"] == 20
    await setv(e, "sensor.kontakt", "open")
    assert e.pos[-1].data["position"] == 100
    e.c.settings["night_open_pos"] = 60
    await setv(e, "sensor.kontakt", "closed")
    await setv(e, "sensor.kontakt", "open")
    assert e.pos[-1].data["position"] == 60
    await setv(e, "input_boolean.tag", "on")
    assert e.pos[-1].data["position"] == 100


async def test_night_ignores_shading(hass, freezer):
    e = await setup(hass, freezer)
    await setv(e, "input_boolean.tag", "off")
    n = n_cmds(e)
    shading_inputs_ok(e)
    await setv(e, "sensor.lux", "50000")
    assert n_cmds(e) == n and not e.c.shading


async def test_day_contact_has_no_effect(hass, freezer):
    e = await setup(hass, freezer)
    n = n_cmds(e)
    await setv(e, "sensor.kontakt", "open")
    await setv(e, "sensor.kontakt", "tilted")
    assert n_cmds(e) == n


async def test_lockout_only_when_up(hass, freezer):
    e = await setup(hass, freezer)
    e.c.settings["lockout"] = True
    await setv(e, "sensor.kontakt", "open")       # Rollo oben (100)
    await setv(e, "input_boolean.tag", "off")
    assert not e.pos and e.c.blocked
    await setv(e, "sensor.kontakt", "closed")
    await tick(e, 29)
    assert not e.pos
    await tick(e, 2)
    assert e.pos[-1].data["position"] == 0 and not e.c.blocked
    # Rollo nicht oben: Kontakt offen sperrt nicht
    await setv(e, COVER, "open", {"current_position": 40, "supported_features": 15})
    await setv(e, "input_boolean.tag", "on")
    await setv(e, COVER, "open", {"current_position": 40, "supported_features": 15})
    await setv(e, "sensor.kontakt", "open")
    await setv(e, "input_boolean.tag", "off")
    assert e.pos[-1].data["position"] == 100 and not e.c.blocked


async def test_lockout_reopen_cancels_and_catches_up_current_target(hass, freezer):
    e = await setup(hass, freezer)
    e.c.settings["lockout"] = True
    await setv(e, "sensor.kontakt", "open")
    await setv(e, "input_boolean.tag", "off")
    await setv(e, "sensor.kontakt", "tilted")
    await tick(e, 10)
    await setv(e, "sensor.kontakt", "open")      # wieder offen -> Nachholen verworfen
    await tick(e, 60)
    assert not e.pos
    await setv(e, "sensor.kontakt", "tilted")
    await tick(e, 31)
    assert e.pos[-1].data["position"] == 20      # aktuell gueltiges Ziel (gekippt), nicht "geschlossen"


async def test_lockout_blocks_shading_start(hass, freezer):
    e = await setup(hass, freezer)
    e.c.settings["lockout"] = True
    await setv(e, "sensor.kontakt", "open")
    shading_inputs_ok(e)
    await setv(e, "sensor.lux", "40001")
    assert e.c.blocked and not e.pos
    await setv(e, "sensor.kontakt", "closed")
    await tick(e, 31)
    assert e.pos[-1].data["position"] == 30


async def test_shading_start_end_delay(hass, freezer):
    e = await setup(hass, freezer)
    shading_inputs_ok(e)
    await setv(e, "sensor.lux", "40001")
    assert e.c.shading and e.pos[-1].data["position"] == 30
    assert e.c.pre_pos == 100
    n = n_cmds(e)
    await setv(e, "sensor.lux", "10000")
    assert e.c.phase == "shading_ending"
    await tick(e, 200)
    await setv(e, "sensor.lux", "25000")
    assert e.c.phase == "shading"
    await tick(e, 400)
    assert e.c.shading and n_cmds(e) == n
    await setv(e, "sensor.aussen", "5")
    await tick(e, 299)
    assert e.c.shading
    await tick(e, 2)
    assert not e.c.shading and e.pos[-1].data["position"] == 100


async def test_shading_previous_position_and_up(hass, freezer):
    e = await setup(hass, freezer)
    await setv(e, COVER, "open", {"current_position": 70, "supported_features": 15})
    shading_inputs_ok(e)
    await setv(e, "sensor.lux", "40001")
    assert e.c.pre_pos == 70
    await setv(e, "sensor.elev", "5")
    await tick(e, 301)
    assert e.pos[-1].data["position"] == 70
    e.c.settings["shade_end"] = "up"
    e.c.settings["day_pos"] = 90
    await setv(e, "sensor.elev", "30")
    assert e.c.shading
    await setv(e, "sensor.azi", "300")
    await tick(e, 301)
    assert not e.c.shading and e.pos[-1].data["position"] == 90


async def test_manual_command_does_not_pause_automation(hass, freezer):
    e = await setup(hass, freezer)
    shading_inputs_ok(e)
    await setv(e, "sensor.lux", "40001")
    n = len(e.pos)
    await e.c.async_command("up")
    assert len(e.open) == 1 and e.c.shading
    await setv(e, "sensor.lux", "41000")
    assert len(e.pos) == n
    await setv(e, "sensor.lux", "1")
    await tick(e, 301)
    assert e.pos[-1].data["position"] == 100


async def test_day_start_with_shading(hass, freezer):
    e = await setup(hass, freezer)
    await setv(e, "input_boolean.tag", "off")
    shading_inputs_ok(e)
    await setv(e, "input_boolean.tag", "on")
    assert e.c.shading and e.pos[-1].data["position"] == 30


async def test_mypos_targets_ignore_shading_values(hass, freezer):
    e = await setup(hass, freezer, shade_entity="button.mypos")
    pressed = async_mock_service(hass, "button", "press")
    c = e.c
    c.settings["night_closed_mode"] = "mypos"
    await setv(e, "input_boolean.tag", "off")
    assert pressed and not e.pos                  # MyPosition statt Position
    c.settings["night_closed_mode"] = "position"
    # Tag: Beschattung als Position -> Position aus shade_pos, kein MyPosition
    await setv(e, "input_boolean.tag", "on")
    n = len(pressed)
    shading_inputs_ok(e)
    await setv(e, "sensor.lux", "40001")
    assert len(pressed) == n and e.pos[-1].data["position"] == 30
    c.settings["shade_mode"] = "mypos"
    await setv(e, "sensor.lux", "10000")
    await tick(e, 301)
    await setv(e, "sensor.lux", "40002")
    assert len(pressed) == n + 1                  # Beschattung per MyPosition


async def test_mode_selects_only_position_and_mypos(hass, freezer):
    e = await setup(hass, freezer, shade_entity="button.mypos")
    st = hass.states.get(e.ids["night_open_mode"])
    assert st.attributes["options"] == ["position", "mypos"]
    e2 = hass.states.get(e.ids["day_mode"])
    assert e2.attributes["options"] == ["position", "mypos"]


async def test_back_button(hass, freezer):
    e = await setup(hass, freezer)
    await setv(e, "input_boolean.tag", "off")
    await setv(e, "sensor.kontakt", "tilted")
    assert e.pos[-1].data["position"] == 20
    await e.c.async_command("up")                 # manuell
    await hass.services.async_call("button", "press", {"entity_id": e.ids["button_back"]}, blocking=True)
    assert e.pos[-1].data["position"] == 20       # letzte automatische Nacht-Position
    await setv(e, "input_boolean.tag", "on")
    await e.c.async_command("down")
    await e.c.async_command("back")
    assert e.pos[-1].data["position"] == 100


async def test_internal_position_linear(hass, freezer):
    e = await setup(hass, freezer, position_source="internal", shade_entity="button.mypos")
    pressed = async_mock_service(hass, "button", "press")
    c = e.c
    c.tracker.set(100)
    c.settings.update(time_down=20, time_up=40, mypos_pos=50)
    await c.drive_down()
    await tick(e, 10)
    assert round(c.tracker.current()) == 50
    await c.drive_stop()
    base = len(e.stop)
    await c.drive_pos(75)                         # 25 % hoch = 10 s
    await tick(e, 9)
    assert len(e.stop) == base
    await tick(e, 2)
    assert len(e.stop) == base + 1 and round(c.tracker.current()) == 75
    c.tracker.set(100)
    await c.drive_mypos()
    assert pressed
    await tick(e, 11)
    assert round(c.tracker.current()) == 50


async def test_calibration_two_steps(hass, freezer):
    e = await setup(hass, freezer, position_source="internal", shade_entity="button.mypos")
    async_mock_service(hass, "button", "press")
    c = e.c
    c.set_calibration("down")
    await c.async_command("mypos")                # Start per MyPosition
    await tick(e, 22)
    await c.async_command("stop")
    assert c.settings["time_down"] == 22 and c.calibration == "up"
    assert c.tracker.current() == 0
    await c.async_command("up")
    await tick(e, 31)
    await c.async_command("stop")
    assert c.settings["time_up"] == 31 and c.calibration == "mypos"
    assert c.tracker.current() == 100
    # Schritt 3: MyPosition von oben, Motor haelt nach 10 s selbst, dann Stopp
    await c.async_command("mypos")
    await tick(e, 10)
    await c.async_command("stop")
    assert c.settings["mypos_pos"] == 55 and c.calibration == "off"   # 100 - 100*10/22
    assert round(c.tracker.current()) == 55


async def test_calibration_without_mypos_has_two_steps(hass, freezer):
    e = await setup(hass, freezer, position_source="internal")
    c = e.c
    assert c.calibration_steps == ["down", "up"]
    st = hass.states.get(e.ids["calibration"])
    assert st.attributes["options"] == ["off", "down", "up"]
    c.set_calibration("up")
    await c.async_command("up")
    await tick(e, 20)
    await c.async_command("stop")
    assert c.calibration == "off"


async def test_entities_and_external(hass, freezer):
    hass.states.async_set("sensor.extern", "none")
    e = await setup(hass, freezer, external_entity="sensor.extern")
    for k in ("night_open_pos", "shade_end_delay", "lockout", "button_up", "button_back",
              "state", "target_position", "shading", "diagnostics"):
        assert k in e.ids, k
    for k in ("calibration", "time_down", "hide_times", "mypos_pos", "slat_shade",
              "shade_mode", "button_mypos", "button_shade", "target_slat", "position"):
        assert k not in e.ids, k
    await hass.services.async_call("number", "set_value",
        {"entity_id": e.ids["target_position"], "value": 40}, blocking=True)
    assert e.pos[-1].data["position"] == 40
    await setv(e, "sensor.extern", "Runter")
    assert len(e.close) == 1
    d = hass.states.get(e.ids["diagnostics"])
    assert d.state == "ok" and d.attributes["tag_erkannt"] is True
    await hass.services.async_call("button", "press", {"entity_id": e.ids["button_stop"]}, blocking=True)
    assert len(e.stop) == 1


async def test_internal_entities_and_hide_times(hass, freezer):
    e = await setup(hass, freezer, position_source="internal", use_tilt=True,
                    shade_entity="button.mypos")
    for k in ("calibration", "time_down", "time_up", "mypos_pos", "hide_times", "slat_night_tilted", "slat_day", "shade_mode",
              "button_mypos", "target_slat"):
        assert k in e.ids, k
    reg = er.async_get(hass)
    assert reg.async_get(e.ids["time_down"]).hidden_by is None
    await hass.services.async_call("switch", "turn_on", {"entity_id": e.ids["hide_times"]}, blocking=True)
    await hass.async_block_till_done()
    for k in ("time_down", "time_up", "mypos_pos", "calibration"):
        assert reg.async_get(e.ids[k]).hidden_by == er.RegistryEntryHider.INTEGRATION, k
    await hass.services.async_call("switch", "turn_off", {"entity_id": e.ids["hide_times"]}, blocking=True)
    await hass.async_block_till_done()
    assert reg.async_get(e.ids["time_down"]).hidden_by is None
    await hass.services.async_call("number", "set_value",
        {"entity_id": e.ids["target_slat"], "value": 80}, blocking=True)
    assert e.tilt[-1].data["tilt_position"] == 80
    await setv(e, "input_boolean.tag", "off")
    await setv(e, "sensor.kontakt", "tilted")
    assert e.tilt[-1].data["tilt_position"] == 50
    await setv(e, "input_boolean.tag", "on")
    assert e.tilt[-1].data["tilt_position"] == 100


async def test_lockout_default_by_type(hass, freezer):
    e = await setup(hass, freezer, device_type="door")
    assert e.c.settings["lockout"] is True
    e2 = await setup(hass, freezer, device_type="window")
    assert e2.c.settings["lockout"] is False


async def test_config_flow(hass):
    hass.states.async_set(COVER, "open", {"supported_features": 15})
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert r["type"] == "form"
    from homeassistant.data_entry_flow import InvalidData
    with pytest.raises(InvalidData):  # Tag-Quelle ist Pflicht
        await hass.config_entries.flow.async_configure(
            r["flow_id"], {"name": "X", "cover": COVER, "position_source": "device", "use_tilt": False,
                           "device_type": "window", "contact_open": "a", "contact_tilted": "b",
                           "contact_closed": "c"})
    r = await hass.config_entries.flow.async_configure(
        r["flow_id"], {"name": "X", "cover": COVER, "day_entity": "input_boolean.tag",
                       "device_type": "door",
                       "position_source": "device", "use_tilt": False,
                       "contact_open": "open", "contact_tilted": "tilted", "contact_closed": "closed"})
    assert r["type"] == "create_entry" and r["title"] == "X"




async def test_resource_registration(hass):
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    from custom_components.rollladen_steuerung import CARD_URL, _async_register_resource

    class Res:
        loaded = True
        def __init__(self, items): self.items = items; self.created = []; self.updated = []
        def async_items(self): return self.items
        async def async_create_item(self, d): self.created.append(d)
        async def async_update_item(self, i, d): self.updated.append((i, d))

    class Data:
        def __init__(self, res, mode="storage"): self.resources = res; self.resource_mode = mode

    res = Res([])
    hass.data[LOVELACE_DATA] = Data(res)
    assert await _async_register_resource(hass, CARD_URL + "?v=1")
    assert res.created == [{"res_type": "module", "url": CARD_URL + "?v=1"}]
    res2 = Res([{"id": "x", "url": CARD_URL}])
    hass.data[LOVELACE_DATA] = Data(res2)
    assert await _async_register_resource(hass, CARD_URL + "?v=2")
    assert res2.updated[0][0] == "x" and not res2.created
    hass.data[LOVELACE_DATA] = Data(Res([]), mode="yaml")
    assert not await _async_register_resource(hass, CARD_URL)


async def test_late_closing_echo_does_not_restart_tracker(hass, freezer):
    e = await setup(hass, freezer, position_source="internal")
    c = e.c
    c.tracker.set(100)
    c.settings.update(time_down=20, time_up=20)
    await c.drive_pos(70)
    await setv(e, COVER, "closing", {"supported_features": 15})
    await tick(e, 7)
    assert len(e.stop) == 1 and round(c.tracker.current()) == 70
    await setv(e, COVER, "closing", {"supported_features": 15, "x": 1})   # verspaetetes Echo
    await tick(e, 30)
    assert round(c.tracker.current()) == 70
    await setv(e, COVER, "open", {"supported_features": 15})
    assert round(c.tracker.current()) == 70
    # externer Stopp: Fahrt von oben, nach 3 s meldet das Geraet "open" -> Schaetzung stoppt
    await tick(e, 10)
    c.tracker.set(100)
    await setv(e, COVER, "closing", {"supported_features": 15})
    await tick(e, 5)
    await setv(e, COVER, "open", {"supported_features": 15})
    assert round(c.tracker.current()) == 75
    await tick(e, 20)
    assert round(c.tracker.current()) == 75


async def test_closed_after_stop_midway_is_ignored(hass, freezer):
    e = await setup(hass, freezer, position_source="internal")
    c = e.c
    c.tracker.set(0)
    c.settings.update(time_down=20, time_up=20)
    await c.drive_pos(25)                          # 5 s hoch
    await setv(e, COVER, "opening", {"supported_features": 15})
    await tick(e, 6)
    await setv(e, COVER, "closed", {"supported_features": 15})   # Geraet meldet nach Stopp "closed"
    assert round(c.tracker.current()) == 25
    await tick(e, 3)
    assert round(c.tracker.current()) == 25
    # echte Fahrt nach unten endet mit "closed"
    c.tracker.set(100)
    await c.drive_down()
    await setv(e, COVER, "closing", {"supported_features": 15})
    await tick(e, 10)
    await setv(e, COVER, "closed", {"supported_features": 15, "y": 1})
    assert c.tracker.current() == 0


async def test_calibration_uses_device_state_changes(hass, freezer):
    e = await setup(hass, freezer, position_source="internal", shade_entity="button.mypos")
    async_mock_service(hass, "button", "press")
    c = e.c
    c.settings["time_down"] = 20
    c.tracker.set(100)
    c.set_calibration("mypos")
    await c.async_command("mypos")
    await tick(e, 3)                               # lange Latenz (langer Tastendruck am Sender)
    await setv(e, COVER, "closing", {"supported_features": 15})
    await tick(e, 10)
    await setv(e, COVER, "open", {"supported_features": 15})
    assert c.settings["mypos_pos"] == 50 and c.calibration == "off"   # 10 s von 20 s
    # Stopp-Taste mit Geraetemeldung: Ende kommt vom Geraet
    c.set_calibration("down")
    await c.async_command("down")
    await setv(e, COVER, "closing", {"supported_features": 15, "a": 1})
    await tick(e, 21)
    await c.async_command("stop")
    await tick(e, 1)
    await setv(e, COVER, "closed", {"supported_features": 15})
    assert c.settings["time_down"] == 22 and c.calibration == "up"
    # Geraet meldet das Ende nie: Rueckfall nach 3 s mit Stopp-Zeitpunkt
    await c.async_command("up")
    await setv(e, COVER, "opening", {"supported_features": 15})
    await tick(e, 21)
    await c.async_command("stop")
    await tick(e, 4)
    assert c.settings["time_up"] == 21 and c.calibration == "mypos"


async def test_combined_command_for_height_and_slats(hass, freezer):
    hass.states.async_set(COVER, "open", {"current_position": 100, "current_tilt_position": 100,
                                          "supported_features": 255})
    put = async_mock_service(hass, "homematicip_local", "put_paramset")
    e = await setup(hass, freezer, use_tilt=True, combined_device="abc123", combined_channel=4)
    async_mock_service(hass, "homematicip_local", "put_paramset")
    put = async_mock_service(hass, "homematicip_local", "put_paramset")
    await setv(e, "input_boolean.tag", "off")                  # Nacht, Kontakt geschlossen
    assert len(put) == 1 and not e.pos and not e.tilt
    d = put[0].data
    assert d["device_id"] == "abc123" and d["channel"] == 4 and d["paramset_key"] == "VALUES"
    assert d["paramset"] == {"COMBINED_PARAMETER": "L=0,L2=0"} and d["retry"] is True
    await setv(e, "sensor.kontakt", "tilted")
    assert put[-1].data["paramset"]["COMBINED_PARAMETER"] == "L=20,L2=50"
    # manuell: Hoehe mit aktuellen Lamellen
    await setv(e, COVER, "open", {"current_position": 20, "current_tilt_position": 70, "supported_features": 255})
    await e.c.async_set_position(60)
    assert put[-1].data["paramset"]["COMBINED_PARAMETER"] == "L=60,L2=70"
    await e.c.async_set_slat(30)
    assert put[-1].data["paramset"]["COMBINED_PARAMETER"] == "L=20,L2=30"
    assert not e.pos and not e.tilt


async def test_no_combined_without_device(hass, freezer):
    e = await setup(hass, freezer, use_tilt=True)
    await setv(e, "input_boolean.tag", "off")
    assert e.pos and e.tilt                                  # wie bisher: zwei Befehle


async def test_auto_delay_only_for_automatic_drives(hass, freezer):
    e = await setup(hass, freezer)
    e.c.settings["auto_delay"] = 5
    await setv(e, "input_boolean.tag", "off")
    assert not e.pos and e.c.delay_status()[0].startswith("Automatische Fahrt in")
    await tick(e, 4)
    assert not e.pos
    await tick(e, 2)
    assert e.pos[-1].data["position"] == 0 and e.c.delay_status()[0] == "keine"
    # manuelle Fahrbefehle sofort
    n = n_cmds(e)
    await e.c.async_command("up")
    await e.c.async_set_position(40)
    await e.c.async_command("back")
    assert n_cmds(e) == n + 3
    # neues Ziel waehrend der Wartezeit ersetzt das alte
    n = n_cmds(e)
    await setv(e, "sensor.kontakt", "tilted")
    await tick(e, 3)
    await setv(e, "sensor.kontakt", "open")
    await tick(e, 4)
    assert n_cmds(e) == n
    await tick(e, 2)
    assert n_cmds(e) == n + 1 and e.pos[-1].data["position"] == 100


async def test_auto_delay_zero_is_immediate(hass, freezer):
    e = await setup(hass, freezer)
    await setv(e, "input_boolean.tag", "off")
    assert e.pos


async def test_awning_extends_only_for_shading_and_retracts_at_night(hass, freezer):
    e = await setup(hass, freezer, device_type="awning")
    assert e.c.settings["shade_pos"] == 0 and e.c.settings["lockout"] is False
    for k in ("night_open_pos", "night_closed_mode", "lockout", "slat_day", "target_slat"):
        assert k not in e.ids, k
    assert "shade_pos" in e.ids and "auto_hold" in e.ids
    st = hass.states.get(e.ids["state"])
    assert st.attributes["device_type"] == "awning"
    # Tag/Nacht-Wechsel ohne Beschattung: Nacht = einfahren (100), Tag = nichts
    await setv(e, "input_boolean.tag", "off")
    assert e.pos[-1].data["position"] == 100
    n = n_cmds(e)
    await setv(e, "sensor.kontakt", "open")          # Kontakt ohne Wirkung
    assert n_cmds(e) == n
    await setv(e, "input_boolean.tag", "on")
    assert n_cmds(e) == n                            # am Tag keine Fahrt
    # Beschattung = ausfahren (0), Ende = einfahren
    shading_inputs_ok(e)
    await setv(e, "sensor.lux", "50000")
    assert e.pos[-1].data["position"] == 0 and e.c.shading
    await setv(e, "sensor.lux", "0")
    await tick(e, 301)
    assert e.pos[-1].data["position"] == 100
    # Nachtbeginn waehrend Beschattung -> einfahren
    shading_inputs_ok(e)
    await setv(e, "sensor.lux", "50000")
    assert e.pos[-1].data["position"] == 0
    await setv(e, "input_boolean.tag", "off")
    assert e.pos[-1].data["position"] == 100 and not e.c.shading


async def test_awning_day_start_with_shading_extends(hass, freezer):
    e = await setup(hass, freezer, device_type="awning")
    await setv(e, "input_boolean.tag", "off")
    shading_inputs_ok(e)
    n = n_cmds(e)
    await setv(e, "input_boolean.tag", "on")
    assert e.pos[-1].data["position"] == 0 and n_cmds(e) == n + 1


async def test_external_position_commands(hass, freezer):
    hass.states.async_set("sensor.extern", "none")
    e = await setup(hass, freezer, external_entity="sensor.extern")
    await setv(e, "sensor.extern", "position:40")
    assert e.pos[-1].data["position"] == 40
    await setv(e, "sensor.extern", "25")
    assert e.pos[-1].data["position"] == 25
    await setv(e, "sensor.extern", "Pos 70 %")
    assert e.pos[-1].data["position"] == 70
    await setv(e, "sensor.extern", "250")             # begrenzt auf 100
    assert e.pos[-1].data["position"] == 100
    n = n_cmds(e)
    await setv(e, "sensor.extern", "blocked")         # kein Kommando mehr
    assert n_cmds(e) == n and not e.c.hold


async def test_external_block_input_party_mode(hass, freezer):
    hass.states.async_set("input_boolean.block", "off")
    e = await setup(hass, freezer, block_entity="input_boolean.block")
    assert "input_block" in e.ids
    await setv(e, "input_boolean.block", "on")
    assert e.c.hold
    n = n_cmds(e)
    await setv(e, "input_boolean.tag", "off")
    assert n_cmds(e) == n and e.c.held_back
    assert "gesperrt" in e.c.delay_status()[0]
    await e.c.async_command("up")                      # manuell geht trotzdem
    assert len(e.open) == 1
    await setv(e, "input_boolean.block", "unavailable")  # unklar = unveraendert
    assert e.c.hold
    await setv(e, "input_boolean.block", "off")
    assert not e.c.hold and e.pos[-1].data["position"] == 0   # Nachtziel nachgeholt
    # Freigabe ohne zurueckgehaltene Fahrt faehrt nicht
    await setv(e, "input_boolean.block", "on")
    n = n_cmds(e)
    await setv(e, "input_boolean.block", "off")
    assert n_cmds(e) == n


async def test_block_input_drives_the_switch(hass, freezer):
    hass.states.async_set("input_boolean.block", "on")
    e = await setup(hass, freezer, block_entity="input_boolean.block")
    sw = e.ids["auto_hold"]
    assert e.c.hold and hass.states.get(sw).state == "on"      # beim Start vom Eingang uebernommen
    await setv(e, "input_boolean.block", "off")
    assert not e.c.hold and hass.states.get(sw).state == "off"  # Eingang schaltet den Schalter aus
    await setv(e, "input_boolean.block", "true")
    assert hass.states.get(sw).state == "on"
    await hass.services.async_call("switch", "turn_off", {"entity_id": sw}, blocking=True)
    await hass.async_block_till_done()
    assert not e.c.hold                                        # von Hand ueberschreibbar
    await setv(e, "input_boolean.block", "false")              # naechste Aenderung des Eingangs gilt wieder
    assert hass.states.get(sw).state == "off"


async def test_hold_catches_up_to_current_target_and_switch(hass, freezer):
    e = await setup(hass, freezer)
    await hass.services.async_call("switch", "turn_on", {"entity_id": e.ids["auto_hold"]}, blocking=True)
    await hass.async_block_till_done()
    assert e.c.hold
    n = n_cmds(e)
    await setv(e, "input_boolean.tag", "off")           # Nacht, zurueckgehalten
    await setv(e, "sensor.kontakt", "tilted")           # Ziel aendert sich waehrend der Sperre
    await setv(e, "input_boolean.tag", "on")            # wieder Tag
    shading_inputs_ok(e)
    await setv(e, "sensor.lux", "50000")                # Beschattung beginnt
    assert n_cmds(e) == n and e.c.shading
    await hass.services.async_call("switch", "turn_off", {"entity_id": e.ids["auto_hold"]}, blocking=True)
    await hass.async_block_till_done()
    assert e.pos[-1].data["position"] == 30 and n_cmds(e) == n + 1   # aktuelles Ziel: Beschattung


async def test_hold_with_auto_delay_keeps_waiting_drive(hass, freezer):
    e = await setup(hass, freezer)
    e.c.settings["auto_delay"] = 5
    await setv(e, "input_boolean.tag", "off")
    await hass.services.async_call("switch", "turn_on", {"entity_id": e.ids["auto_hold"]}, blocking=True)
    await tick(e, 6)
    assert not e.pos
    await hass.services.async_call("switch", "turn_off", {"entity_id": e.ids["auto_hold"]}, blocking=True)
    await tick(e, 6)
    assert e.pos[-1].data["position"] == 0
