"""Config-flow transition tests with an HA API double (not a real HA runtime)."""
import asyncio
from copy import deepcopy
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def module(name, **attrs):
    result = ModuleType(name)
    result.__dict__.update(attrs)
    sys.modules[name] = result
    return result


class Flow:
    def __init_subclass__(cls, **kwargs):
        pass
    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}
    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}
    async def async_set_unique_id(self, value):
        self.unique_id = value
    def _abort_if_unique_id_configured(self):
        pass
    def _get_reauth_entry(self):
        return self.entry
    def _abort_if_unique_id_mismatch(self):
        if self.unique_id != self.entry.unique_id:
            raise AssertionError("unique_id changed")
    def async_update_and_abort(self, entry, *, data_updates):
        entry.data = {**entry.data, **data_updates}
        return {"type": "abort", "reason": "reauth_successful"}


module("voluptuous", Schema=lambda fields: fields, Optional=lambda key, **kwargs: key, Required=lambda key, **kwargs: key)
entries = module("homeassistant.config_entries", ConfigFlow=Flow, OptionsFlow=Flow)
module("homeassistant", config_entries=entries)
module("homeassistant.core", callback=lambda fn: fn)
er = module("homeassistant.helpers.entity_registry", async_get=lambda hass: hass.registry)
select = module("homeassistant.helpers.selector")
for name in ("EntitySelector", "EntitySelectorConfig", "SelectSelector", "SelectSelectorConfig", "TextSelector", "TextSelectorConfig"):
    setattr(select, name, lambda *args, **kwargs: kwargs or args)
select.SelectSelectorMode = SimpleNamespace(DROPDOWN="dropdown")
select.TextSelectorType = SimpleNamespace(PASSWORD="password")
module("homeassistant.helpers", entity_registry=er, selector=select)
dr = module("homeassistant.helpers.device_registry", async_get=lambda hass: SimpleNamespace(async_get=lambda device_id: None))
sys.modules["homeassistant.helpers"].device_registry = dr
module("homeassistant.helpers.aiohttp_client", async_get_clientsession=lambda hass: None)
package = module("ne_adapter")
package.__path__ = [str(Path(__file__).resolve().parents[1] / "custom_components/nase_energie")]
flow = importlib.import_module("ne_adapter.config_flow")


class ConfigTransitions(unittest.IsolatedAsyncioTestCase):
    def make_flow(self):
        instance = flow.ConfigFlow()
        states = [SimpleNamespace(entity_id="sensor.pv", state="1", attributes={"unit_of_measurement": "kW"})]
        instance.hass = SimpleNamespace(states=SimpleNamespace(async_all=lambda domain: states), registry=SimpleNamespace(entities={}))
        return instance

    async def test_code_not_exchanged_before_sensor_consent(self):
        instance = self.make_flow()
        result = await instance.async_step_user({"portal_url": "https://portal.test", "pairing_code": "ne_" + "A" * 32})
        self.assertEqual(result["step_id"], "measurements")
        result = await instance.async_step_measurements({"pv_w": ["sensor.pv"]})
        self.assertEqual(result["step_id"], "confirm")
        result = await instance.async_step_confirm({"grid_sign": "1", "battery_sign": "1", "enabled": True, "consent": False})
        self.assertEqual(result["errors"], {"base": "consent_required"})
        self.assertTrue(instance._code)

    async def test_claim_creates_entry_without_pair_code(self):
        instance = self.make_flow()
        await instance.async_step_user({"portal_url": "https://portal.test", "pairing_code": "ne_" + "A" * 32})
        await instance.async_step_measurements({"pv_w": ["sensor.pv"]})
        original = flow.PortalClient
        class Client:
            def __init__(self, *args):
                pass
            async def pair(self, code):
                return {"token": "synthetic", "installation": {"id": 1, "name": "Demo"}}
        flow.PortalClient = Client
        try:
            result = await instance.async_step_confirm({"grid_sign": "-1", "battery_sign": "-1", "enabled": True, "consent": True})
        finally:
            flow.PortalClient = original
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["data"]["mapping"]["pv_w"], ["sensor.pv"])
        self.assertEqual(result["data"]["signs"]["grid_w"], -1)
        self.assertNotIn("pairing_code", result["data"])
        self.assertEqual(instance._code, "")

    async def test_duplicate_measurement_rejected(self):
        instance = self.make_flow()
        result = await instance.async_step_measurements({"pv_w": ["sensor.pv"], "load_w": "sensor.pv"})
        self.assertEqual(result["errors"], {"base": "duplicate_sensor"})

    async def test_bad_url_rejected_before_discovery(self):
        result = await self.make_flow().async_step_user({"portal_url": "http://portal.test", "pairing_code": "ne_" + "A" * 32})
        self.assertEqual(result["errors"], {"base": "invalid_url"})

    async def test_options_can_pause_without_claim(self):
        instance = flow.OptionsFlow()
        instance.hass = self.make_flow().hass
        instance.config_entry = SimpleNamespace(data={"mapping": {"pv_w": ["sensor.pv"]}, "signs": {"grid_w": 1, "battery_w": 1}}, options={})
        result = await instance.async_step_init({"pv_w": ["sensor.pv"]})
        self.assertEqual(result["step_id"], "confirm")
        result = await instance.async_step_confirm({"grid_sign": "1", "battery_sign": "1", "enabled": False, "consent": True})
        self.assertFalse(result["data"]["enabled"])
        self.assertNotIn("token", result["data"])

    async def test_options_add_strings_with_consent(self):
        instance = flow.OptionsFlow()
        instance.hass = self.make_flow().hass
        instance.config_entry = SimpleNamespace(data={"mapping": {"pv_w": ["sensor.pv"]}, "signs": {"grid_w": 1, "battery_w": 1}}, options={})
        await instance.async_step_init({"pv_w": ["sensor.pv"], "pv_strings": ["sensor.pv"]})
        result = await instance.async_step_confirm({"grid_sign": "1", "battery_sign": "1", "enabled": True, "consent": True})
        self.assertEqual(len(result["data"]["pv_strings"]), 1)
        self.assertEqual(result["data"]["pv_strings"][0]["entity_id"], "sensor.pv")

    async def test_options_preserve_explicit_no_strings(self):
        instance = flow.OptionsFlow()
        instance.hass = self.make_flow().hass
        instance.config_entry = SimpleNamespace(data={"mapping": {"pv_w": ["sensor.pv"]}, "signs": {}, "pv_strings": []}, options={})
        result = await instance.async_step_init()
        self.assertIn("pv_strings", result["data_schema"])

    async def test_options_preserve_unrelated_settings(self):
        instance = flow.OptionsFlow()
        instance.hass = self.make_flow().hass
        instance.config_entry = SimpleNamespace(
            data={"mapping": {"pv_w": ["sensor.pv"]}, "signs": {}},
            options={"future_option": {"keep": True}, "enabled": False})
        await instance.async_step_init({"pv_w": ["sensor.pv"]})
        result = await instance.async_step_confirm({"grid_sign": "1", "battery_sign": "1",
                                                   "enabled": False, "consent": True})
        self.assertEqual(result["data"]["future_option"], {"keep": True})
        self.assertFalse(result["data"]["enabled"])

    def reauth_flow(self):
        instance = self.make_flow()
        instance.entry = SimpleNamespace(
            data={"portal_url": "https://portal.test", "installation_id": 42, "token": "old",
                  "mapping": {"pv_w": ["sensor.pv"]}, "signs": {"grid_w": -1},
                  "pv_strings": [{"id": "s_saved", "entity_id": "sensor.pv"}], "enabled": False},
            options={"mapping": {"pv_w": ["sensor.pv"]}, "enabled": False, "future": "keep"},
            title="User-defined name", entry_id="preserved-entry", unique_id="https://portal.test|42")
        return instance

    async def test_reauth_preserves_everything_except_token(self):
        instance = self.reauth_flow()
        before = deepcopy(vars(instance.entry))
        original = flow.PortalClient
        class Client:
            def __init__(self, session, url):
                self.url = url
            async def pair(self, code):
                return {"token": "new", "installation": {"id": 42, "name": "Server name changed"}}
        flow.PortalClient = Client
        try:
            form = await instance.async_step_reauth(instance.entry.data)
            self.assertEqual(form["step_id"], "reauth_confirm")
            result = await instance.async_step_reauth_confirm({"pairing_code": "ne_" + "A"*32, "consent": True})
        finally:
            flow.PortalClient = original
        expected = deepcopy(before)
        expected["data"]["token"] = "new"
        self.assertEqual(vars(instance.entry), expected)
        self.assertEqual(result, {"type": "abort", "reason": "reauth_successful"})
        self.assertFalse(instance.entry.options["enabled"])

    async def test_reauth_wrong_installation_preserves_old_entry(self):
        instance = self.reauth_flow()
        before = deepcopy(vars(instance.entry))
        original = flow.PortalClient
        class Client:
            def __init__(self, *args):
                pass
            async def pair(self, code):
                return {"token": "wrong-new", "installation": {"id": 99}}
        flow.PortalClient = Client
        try:
            result = await instance.async_step_reauth_confirm({"pairing_code": "ne_" + "B"*32, "consent": True})
        finally:
            flow.PortalClient = original
        self.assertEqual(result["errors"], {"base": "wrong_installation"})
        self.assertEqual(vars(instance.entry), before)

    async def test_reauth_no_consent_does_not_claim_code(self):
        instance = self.reauth_flow()
        original = flow.PortalClient
        def never_called(*args):
            raise AssertionError("no consent")
        flow.PortalClient = never_called
        try:
            result = await instance.async_step_reauth_confirm({"pairing_code": "ne_" + "A"*32, "consent": False})
        finally:
            flow.PortalClient = original
        self.assertEqual(result["errors"], {"base": "consent_required"})

    async def test_reauth_invalid_code_does_not_modify_entry(self):
        instance = self.reauth_flow()
        before = deepcopy(vars(instance.entry))
        result = await instance.async_step_reauth_confirm({"pairing_code": "bad", "consent": True})
        self.assertEqual(result["errors"], {"base": "invalid_pairing"})
        self.assertEqual(vars(instance.entry), before)

    async def test_reauth_network_error_does_not_modify_entry(self):
        instance = self.reauth_flow()
        before = deepcopy(vars(instance.entry))
        original = flow.PortalClient
        class Client:
            def __init__(self, *args):
                pass
            async def pair(self, code):
                raise flow.PortalError("cannot_connect")
        flow.PortalClient = Client
        try:
            result = await instance.async_step_reauth_confirm({"pairing_code": "ne_" + "A"*32, "consent": True})
        finally:
            flow.PortalClient = original
        self.assertEqual(result["errors"], {"base": "cannot_connect"})
        self.assertEqual(vars(instance.entry), before)

