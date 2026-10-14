"""Setup/migration lifecycle tests with API doubles; actual HA tests are separate."""
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
    result = sys.modules.setdefault(name, ModuleType(name))
    result.__dict__.update(attrs)
    return result


module("homeassistant.const", Platform=SimpleNamespace(SENSOR="sensor"))
module("homeassistant.core", callback=lambda fn: fn)
module("homeassistant.helpers.aiohttp_client", async_get_clientsession=lambda hass: None)
module("homeassistant.helpers.event", async_track_time_interval=lambda *args: (lambda: None))
package = ModuleType("ne_entry_tests")
package.__path__ = [str(Path(__file__).resolve().parents[1] / "custom_components/nase_energie")]
sys.modules[package.__name__] = package
e = importlib.import_module(package.__name__ + ".__init__")
diag = importlib.import_module(package.__name__ + ".diagnostics")


class EntryLifecycle(unittest.IsolatedAsyncioTestCase):
    async def test_migration_calls_update_with_preserved_data_and_options(self):
        entry = SimpleNamespace(version=1, minor_version=1, data={"token": "synthetic", "mapping": {}},
                                options={"enabled": False, "keep": "saved"})
        updates = []
        hass = SimpleNamespace(config_entries=SimpleNamespace(async_update_entry=lambda entry, **values: updates.append(values)))
        before = deepcopy(vars(entry))
        self.assertTrue(await e.async_migrate_entry(hass, entry))
        self.assertEqual(updates, [{"data": {**entry.data, "pv_strings": []}, "options": entry.options,
                                    "version": 1, "minor_version": 2}])
        self.assertEqual(vars(entry), before)

    async def test_unknown_schema_does_not_write_or_reset(self):
        entry = SimpleNamespace(version=2, minor_version=1, data={"token": "synthetic"}, options={})
        updates = []
        hass = SimpleNamespace(config_entries=SimpleNamespace(async_update_entry=lambda *args, **kwargs: updates.append(kwargs)))
        with self.assertLogs(e.__name__, level="ERROR"):
            self.assertFalse(await e.async_migrate_entry(hass, entry))
        self.assertEqual(updates, [])

    async def test_sender_reauth_callback_targets_the_same_entry(self):
        repairs, listeners = [], []
        entry = SimpleNamespace(data={"portal_url": "https://portal.test", "token": "synthetic", "mapping": {},
                                      "signs": {}, "enabled": False}, options={},
                                async_start_reauth=lambda hass: repairs.append(hass),
                                add_update_listener=lambda fn: listeners.append(fn),
                                async_on_unload=lambda callback: None)
        async def forward(*args):
            return None
        hass = SimpleNamespace(async_create_task=asyncio.create_task,
                               config_entries=SimpleNamespace(async_forward_entry_setups=forward))
        self.assertTrue(await e.async_setup_entry(hass, entry))
        await asyncio.sleep(0)
        entry.runtime_data.auth_failed()
        self.assertEqual(repairs, [hass])
        self.assertEqual(listeners, [e.async_reload_entry])
        await entry.runtime_data.close()

    async def test_diagnostics_never_leak_credentials_or_entity_ids(self):
        sender = SimpleNamespace(status="online", settings={"token": "synthetic-secret", "portal_url": "https://private.test",
                                                            "mapping": {"pv_w": ["sensor.private"]}}, queue=[], dropped=0)
        result = await diag.async_get_config_entry_diagnostics(None, SimpleNamespace(runtime_data=sender))
        serialized = str(result)
        for private in ("synthetic-secret", "private.test", "sensor.private"):
            self.assertNotIn(private, serialized)
        self.assertEqual(result["integration_version"], diag.INTEGRATION_VERSION)

    async def test_unloaded_entry_can_supply_safe_diagnostics(self):
        self.assertEqual((await diag.async_get_config_entry_diagnostics(None, SimpleNamespace()))["status"], "not_loaded")
