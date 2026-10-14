"""Validate and package an allowlisted public repository; never read HA config."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "nase_energie"
REPOSITORY = "kullalukas-png/nase-energie-ha"
ROOT_FILES = {"README.md", "LICENSE", "CHANGELOG.md", "SECURITY.md", "CONTRIBUTING.md",
              "hacs.json", "pyproject.toml", ".gitignore", ".gitattributes"}
SOURCE_DIRS = {"custom_components", "docs", "tests", "tests_ha", "tools", ".github", "requirements"}
SECRET_PATTERN = re.compile(r"(?:fve_[A-Za-z0-9_-]{43}|ne_[A-Za-z0-9_-]{32}|gh[pousr]_[A-Za-z0-9]{30,}|"
                            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)")


def public_files(root=ROOT):
    """Only known project files; caches, environments and unrelated data are excluded."""
    for file in sorted(root.rglob("*")):
        if not file.is_file() or file.is_symlink():
            continue
        relative = file.relative_to(root)
        if any(part in {"__pycache__", ".git", ".venv", ".pytest_cache", ".storage", "dist", "node_modules"}
               for part in relative.parts) or file.suffix in {".pyc", ".pyo", ".log", ".db", ".sqlite", ".zip"}:
            continue
        if file.name in {"secrets.yaml", "configuration.yaml"} or file.name.startswith(".env"):
            continue
        if (len(relative.parts) == 1 and file.name in ROOT_FILES) or relative.parts[0] in SOURCE_DIRS:
            yield file


def leaf_keys(value, prefix=""):
    if isinstance(value, dict):
        return {key for name, child in value.items() for key in leaf_keys(child, prefix + "." + name)}
    return {prefix}


def validate_translation_keys(value):
    """Mirror hassfest's key shape so selector labels fail locally, not after upload."""
    if not isinstance(value, dict):
        return
    for key, child in value.items():
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?", key):
            raise ValueError("Invalid translation key: " + key)
        validate_translation_keys(child)


def release_notes(changelog, version):
    match = re.search(r"^## " + re.escape(version) + r"(?:\s|$).*?\n(.*?)(?=^## |\Z)",
                      changelog, re.MULTILINE | re.DOTALL)
    if not match or "DOPLNIT" in match.group(1):
        raise ValueError("Complete the changelog for this version before publishing")
    return match.group(0).strip() + "\n"


def check(root=ROOT, expected_version=None):
    component = root / "custom_components" / DOMAIN
    manifest = json.loads((component / "manifest.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version) or (expected_version and expected_version != version):
        raise ValueError("Release version must match manifest.json exactly")
    if manifest["domain"] != DOMAIN or manifest["codeowners"] != ["@kullalukas-png"]:
        raise ValueError("Integration identity or owner changed")
    if manifest["issue_tracker"] != f"https://github.com/{REPOSITORY}/issues":
        raise ValueError("Issue tracker does not match publication repository")
    if manifest["documentation"] != f"https://github.com/{REPOSITORY}/blob/main/README.md":
        raise ValueError("Documentation does not match publication repository")
    if not manifest.get("config_flow") or manifest["iot_class"] != "cloud_push":
        raise ValueError("Invalid integration metadata")
    constants = ast.parse((component / "const.py").read_text(encoding="utf-8"))
    assignments = {node.targets[0].id: ast.literal_eval(node.value) for node in constants.body
                   if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}
    if assignments["INTEGRATION_VERSION"] != version or assignments["CONFIG_VERSION"] != 1:
        raise ValueError("Version mismatch or unreviewed incompatible configuration schema")
    if not (root / "LICENSE").read_text(encoding="utf-8").startswith("MIT License"):
        raise ValueError("MIT license missing")
    hacs = json.loads((root / "hacs.json").read_text(encoding="utf-8"))
    if hacs.get("homeassistant") != "2026.9.0" or not hacs.get("hide_default_branch"):
        raise ValueError("HACS must offer versioned releases and the tested minimum HA version")
    directories = [p.name for p in (root / "custom_components").iterdir() if p.is_dir() and p.name != "__pycache__"]
    if directories != [DOMAIN]:
        raise ValueError("HACS repository must contain exactly one integration")
    for filename, size in (("icon.png", 256), ("icon@2x.png", 512)):
        image = (component / "brand" / filename).read_bytes()
        if image[:8] != b"\x89PNG\r\n\x1a\n" or struct.unpack(">II", image[16:24]) != (size, size):
            raise ValueError("Local integration brand image missing or invalid")
    original = json.loads((component / "strings.json").read_text(encoding="utf-8"))
    validate_translation_keys(original)
    for language in ("cs", "en"):
        translation = json.loads((component / "translations" / (language + ".json")).read_text(encoding="utf-8"))
        validate_translation_keys(translation)
        if leaf_keys(original) != leaf_keys(translation):
            raise ValueError("Translation keys differ: " + language)
    for file in public_files(root):
        relative = file.relative_to(root).as_posix()
        if file.suffix in {".png", ".jpg"}:
            continue
        source = file.read_text(encoding="utf-8")
        if SECRET_PATTERN.search(source):
            raise ValueError("Possible credential in public source: " + relative)
        if file.suffix == ".py":
            ast.parse(source, filename=relative)
        if file.suffix == ".json":
            json.loads(source)
    notes = release_notes((root / "CHANGELOG.md").read_text(encoding="utf-8"), version)
    return version, notes


def archive(output, root, files):
    """Deterministic ZIPs; refuse to overwrite an existing artifact."""
    with zipfile.ZipFile(output, "x", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for file in files:
            name = file.relative_to(root).as_posix()
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, file.read_bytes(), compresslevel=9)
    with zipfile.ZipFile(output) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)) or bundle.testzip() is not None:
            raise ValueError("Archive validation failed")
        for file in files:
            if bundle.read(file.relative_to(root).as_posix()) != file.read_bytes():
                raise ValueError("Packaged file differs from source")
    return hashlib.sha256(output.read_bytes()).hexdigest()


def build(output, root=ROOT, repository=False):
    version, notes = check(root)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    files = list(public_files(root))
    if not repository:
        files = [p for p in files if p.relative_to(root).parts[:2] == ("custom_components", DOMAIN)
                 or p.name in {"README.md", "LICENSE", "CHANGELOG.md", "SECURITY.md", "CONTRIBUTING.md"}
                 or p.relative_to(root).parts[0] == "docs"]
    name = f"nase-energie-{'repository-' if repository else ''}{version}.zip"
    digest = archive(output / name, root, files)
    (output / ("REPOSITORY-SHA256SUMS.txt" if repository else "SHA256SUMS.txt")).write_text(
        digest + "  " + name + "\n", encoding="utf-8")
    (output / "RELEASE-NOTES.md").write_text(notes, encoding="utf-8")
    return {"file": name, "files": len(files), "bytes": (output / name).stat().st_size, "sha256": digest}


def bump(version, root=ROOT):
    """Mechanical version updates only; config schema is deliberately independent."""
    previous, _ = check(root)
    if not re.fullmatch(r"\d+\.\d+\.\d+", version) or tuple(map(int, version.split("."))) <= tuple(map(int, previous.split("."))):
        raise ValueError("Choose a new, higher X.Y.Z version")
    manifest_path = root / "custom_components" / DOMAIN / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = version
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    const_path = root / "custom_components" / DOMAIN / "const.py"
    source = const_path.read_text(encoding="utf-8").replace(f'INTEGRATION_VERSION = "{previous}"', f'INTEGRATION_VERSION = "{version}"')
    const_path.write_text(source, encoding="utf-8")
    readme_path = root / "README.md"
    readme = readme_path.read_text(encoding="utf-8").replace(f"({previous}, beta)", f"({version}, beta)")
    readme_path.write_text(readme, encoding="utf-8")
    changelog_path = root / "CHANGELOG.md"
    changelog = changelog_path.read_text(encoding="utf-8").replace("# Přehled změn\n", f"# Přehled změn\n\n## {version} — připravované vydání\n\n- DOPLNIT: popis změn a rozsah ověření.\n", 1)
    changelog_path.write_text(changelog, encoding="utf-8")
    print("Version bumped; complete CHANGELOG.md and run the tests before publication.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("check")
    verify.add_argument("--version")
    package = commands.add_parser("build")
    package.add_argument("--output", default="dist")
    package.add_argument("--repository", action="store_true")
    version = commands.add_parser("bump")
    version.add_argument("version")
    args = parser.parse_args()
    if args.command == "check":
        print("Public-source validation OK, version " + check(expected_version=args.version)[0])
    elif args.command == "build":
        print(json.dumps(build(args.output, repository=args.repository), ensure_ascii=False))
    else:
        bump(args.version)


if __name__ == "__main__":
    main()
