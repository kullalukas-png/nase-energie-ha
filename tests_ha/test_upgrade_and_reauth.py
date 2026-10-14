"""Exercise config entry migrations, setup and reauth in actual HA Core."""
from copy import deepcopy
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nase_energie.api import PortalError
from custom_components.nase_energie.const import DOMAIN


def saved_entry(*, enabled=True, strings=False):
    data = {"portal_url": "https://portal.test", "token": "synthetic-old", "installation_id": 42,
            "mapping": {"pv_w": ["sensor.pv"]}, "signs": {"grid_w": -1, "battery_w": -1},
            "enabled": enabled}
    if strings:
        data["pv_strings"] = [{"id": "s_saved", "entity_id": "sensor.pv", "name": "Saved",
                               "inverter_id": "i_saved", "inverter_name": "Saved inverter"}]
    return MockConfigEntry(domain=DOMAIN, title="User-defined name", unique_id="https://portal.test|42",
                           version=1, minor_version=1, data=data,
                           options={"enabled": enabled, "future_option": {"keep": True}})


async def load(hass, entry):
    hass.states.async_set("sensor.pv", "1500", {"unit_of_measurement": "W"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_old_configuration_loads_without_repair_or_new_upload(hass):
    entry = saved_entry(enabled=False)
    original_data, original_options = deepcopy(dict(entry.data)), deepcopy(dict(entry.options))
    original_identity = (entry.entry_id, entry.unique_id, entry.title)
    await load(hass, entry)
    assert entry.version == 1 and entry.minor_version == 2
    assert dict(entry.data) == {**original_data, "pv_strings": []}
    assert dict(entry.options) == original_options
    assert (entry.entry_id, entry.unique_id, entry.title) == original_identity
    assert entry.runtime_data.status == "paused"
    assert hass.config_entries.flow.async_progress() == []


async def test_existing_strings_survive_setup_and_reload(hass):
    entry = saved_entry(strings=True)
    original_data, original_options = deepcopy(dict(entry.data)), deepcopy(dict(entry.options))
    await load(hass, entry)
    assert dict(entry.data) == original_data
    assert dict(entry.options) == original_options
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert dict(entry.data) == original_data
    assert dict(entry.options) == original_options
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_real_reauth_keeps_paused_entry_and_all_options(hass):
    entry = saved_entry(enabled=False, strings=True)
    await load(hass, entry)
    original_data, original_options = deepcopy(dict(entry.data)), deepcopy(dict(entry.options))
    original_identity = (entry.entry_id, entry.unique_id, entry.title)
    entry.async_start_reauth(hass)
    await hass.async_block_till_done()
    progress = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert len(progress) == 1 and progress[0]["context"]["source"] == SOURCE_REAUTH
    with patch("custom_components.nase_energie.config_flow.PortalClient.pair", new_callable=AsyncMock,
               return_value={"token": "synthetic-new", "installation": {"id": 42, "name": "Changed server title"}}):
        result = await hass.config_entries.flow.async_configure(
            progress[0]["flow_id"], {"pairing_code": "ne_" + "A"*32, "consent": True})
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "reauth_successful"
    assert dict(entry.data) == {**original_data, "token": "synthetic-new"}
    assert dict(entry.options) == original_options
    assert (entry.entry_id, entry.unique_id, entry.title) == original_identity
    assert entry.runtime_data.status == "paused"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_wrong_household_code_does_not_repoint_entry(hass):
    entry = saved_entry(enabled=False)
    await load(hass, entry)
    before = deepcopy(dict(entry.data))
    entry.async_start_reauth(hass)
    await hass.async_block_till_done()
    progress = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    with patch("custom_components.nase_energie.config_flow.PortalClient.pair", new_callable=AsyncMock,
               return_value={"token": "synthetic-wrong", "installation": {"id": 99, "name": "Other"}}):
        result = await hass.config_entries.flow.async_configure(
            progress[0]["flow_id"], {"pairing_code": "ne_" + "B"*32, "consent": True})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "wrong_installation"}
    assert dict(entry.data) == before
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_invalid_auth_starts_reauth_and_stops_repeated_sends(hass, no_live_telemetry):
    entry = saved_entry()
    await load(hass, entry)
    no_live_telemetry.reset_mock()
    no_live_telemetry.side_effect = PortalError("invalid_auth")
    await entry.runtime_data.tick()
    await hass.async_block_till_done()
    await entry.runtime_data.tick()
    assert no_live_telemetry.await_count == 1
    assert entry.runtime_data.status == "invalid_auth"
    progress = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert len(progress) == 1 and progress[0]["context"]["source"] == SOURCE_REAUTH
