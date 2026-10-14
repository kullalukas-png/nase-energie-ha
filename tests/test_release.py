"""Public packaging and versioning regressions. Never touch real user settings."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ne_release_tests", ROOT / "tools/release.py")
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class ReleaseTools(unittest.TestCase):
    def test_translation_key_validation_catches_negative_number(self):
        r.validate_translation_keys({"selector": {"grid_w": {"options": {"positive": "Import", "negative": "Export"}}}})
        with self.assertRaises(ValueError):
            r.validate_translation_keys({"selector": {"grid_w": {"options": {"-1": "Export"}}}})

    def test_metadata_and_translations_validate(self):
        manifest = json.loads((ROOT / "custom_components/nase_energie/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(r.check()[0], manifest["version"])

    def test_version_mismatch_blocks_release(self):
        with self.assertRaises(ValueError):
            r.check(expected_version="9.9.9")

    def test_secret_pattern_detects_real_shaped_credentials(self):
        self.assertIsNotNone(r.SECRET_PATTERN.search("fve_" + "A"*43))
        self.assertIsNotNone(r.SECRET_PATTERN.search("ne_" + "B"*32))
        self.assertIsNone(r.SECRET_PATTERN.search("synthetic-old"))

    def test_repository_contains_workflows_not_caches_or_user_data(self):
        with tempfile.TemporaryDirectory() as folder:
            result = r.build(folder, repository=True)
            with zipfile.ZipFile(Path(folder) / result["file"]) as bundle:
                names = bundle.namelist()
                self.assertIn(".github/workflows/publish.yml", names)
                self.assertIn("hacs.json", names)
                self.assertIn("LICENSE", names)
                self.assertIn("tests_ha/test_upgrade_and_reauth.py", names)
                self.assertIn("custom_components/nase_energie/migrations.py", names)
                self.assertIn("custom_components/nase_energie/brand/icon.png", names)
                self.assertIn("custom_components/nase_energie/brand/icon@2x.png", names)
                self.assertFalse(any("__pycache__" in n or n.endswith(".pyc") or ".storage" in n for n in names))

    def test_installation_package_has_only_component_and_user_docs(self):
        with tempfile.TemporaryDirectory() as folder:
            result = r.build(folder)
            with zipfile.ZipFile(Path(folder) / result["file"]) as bundle:
                names = bundle.namelist()
                self.assertIn("custom_components/nase_energie/config_flow.py", names)
                self.assertIn("LICENSE", names)
                self.assertFalse(any(n.startswith(("tests/", "tests_ha/", "tools/", ".github/")) for n in names))

    def test_archives_reproducible_and_not_overwritten(self):
        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            self.assertEqual(r.build(one)["sha256"], r.build(two)["sha256"])
            with self.assertRaises(FileExistsError):
                r.build(one)

    def test_bump_is_mechanical_and_blocks_unfinished_notes(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder) / "project"
            shutil.copytree(ROOT, project, ignore=shutil.ignore_patterns("__pycache__", ".git", ".venv", "dist"))
            migrations_before = (project / "custom_components/nase_energie/migrations.py").read_bytes()
            current, _ = r.check(project)
            numbers = [int(n) for n in current.split(".")]
            next_version = f"{numbers[0]}.{numbers[1]}.{numbers[2]+1}"
            r.bump(next_version, project)
            manifest = json.loads((project / "custom_components/nase_energie/manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["version"], next_version)
            self.assertEqual((project / "custom_components/nase_energie/migrations.py").read_bytes(), migrations_before)
            self.assertIn('CONFIG_MINOR_VERSION = 2', (project / "custom_components/nase_energie/const.py").read_text(encoding="utf-8"))
            with self.assertRaises(ValueError):
                r.check(project, expected_version=next_version)
