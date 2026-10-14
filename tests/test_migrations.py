"""Regression snapshots for upgrades, with no real HA configuration or keys."""
from copy import deepcopy
import importlib
from pathlib import Path
import sys
from types import ModuleType
import unittest

package = ModuleType("ne_migration_tests")
package.__path__ = [str(Path(__file__).resolve().parents[1] / "custom_components/nase_energie")]
sys.modules[package.__name__] = package
m = importlib.import_module(package.__name__ + ".migrations")


class Migrations(unittest.TestCase):
    def settings(self):
        return {
            "portal_url": "https://portal.test", "token": "synthetic-old", "installation_id": 42,
            "mapping": {"pv_w": ["sensor.one", "sensor.two"], "load_w": ["sensor.house"]},
            "signs": {"grid_w": -1, "battery_w": -1}, "enabled": False,
            "future_data": {"keep": [1, 2]},
        }, {"mapping": {"pv_w": ["sensor.saved"]}, "enabled": False, "future_option": {"keep": True}}

    def test_upgrade_01_preserves_all_choices_and_no_new_consent(self):
        data, options = self.settings()
        originals = deepcopy((data, options))
        migrated_data, migrated_options, minor = m.migrate_settings(1, 1, data, options)
        self.assertEqual(migrated_data, {**data, "pv_strings": []})
        self.assertEqual(migrated_options, options)
        self.assertEqual(minor, 2)
        self.assertEqual((data, options), originals)
        migrated_data["future_data"]["keep"].append(3)
        self.assertEqual((data, options), originals)

    def test_upgrade_02_preserves_strings_and_stable_ids(self):
        data, options = self.settings()
        data["pv_strings"] = [{"id": "s_existing", "entity_id": "sensor.string", "name": "Saved"}]
        options["pv_strings"] = []  # User deliberately disabled strings.
        migrated_data, migrated_options, minor = m.migrate_settings(1, 1, data, options)
        self.assertEqual(migrated_data, data)
        self.assertEqual(migrated_options, options)
        self.assertEqual(minor, 2)

    def test_strings_only_in_options_are_preserved(self):
        data, options = self.settings()
        options["pv_strings"] = [{"id": "s_existing", "entity_id": "sensor.saved"}]
        migrated_data, migrated_options, _ = m.migrate_settings(1, 1, data, options)
        self.assertNotIn("pv_strings", migrated_data)
        self.assertEqual(migrated_options, options)

    def test_migration_is_idempotent(self):
        data, options = self.settings()
        first = m.migrate_settings(1, 1, data, options)
        self.assertEqual(m.migrate_settings(1, first[2], first[0], first[1]), first)

    def test_newer_minor_is_not_downgraded(self):
        data, options = self.settings()
        self.assertEqual(m.migrate_settings(1, 8, data, options), (data, options, 8))

    def test_newer_major_rejected_without_wiping_settings(self):
        data, options = self.settings()
        before = deepcopy((data, options))
        with self.assertRaises(ValueError):
            m.migrate_settings(2, 1, data, options)
        self.assertEqual((data, options), before)
