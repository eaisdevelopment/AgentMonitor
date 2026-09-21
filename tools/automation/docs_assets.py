"""Vendor and verify the exact reviewed, offline M2 documentation assets.

`--write` downloads only the reviewed ReDoc tarball in a temporary directory.
`--check` is network-free and fails closed on any missing or changed shipped file.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "frontend/node_modules/swagger-ui-dist"
LOCK = ROOT / "frontend/package-lock.json"
DEST = ROOT / "backend/src/agentmonitor/api/assets/docs"
SWAGGER_VERSION = "5.33.0"
SWAGGER_INTEGRITY = (
    "sha512-wpdK+m6BU5yj6pmUdMskZVTSWYG4DLglAx3sIhylloY37i8O37IrH+YEpqdXNfpaTGxILRBFzUqLF2jKqbfI7A=="
)
REDOC_TARBALL_SHA256 = "44922df4d0eb45c1b066c09ec251e6bd9bd7ded16bc69e87613337b9d911a56e"
APPROVED_SHA256 = {
    "swagger-ui.css": "1ac324f7dcd27e4b9386b4bd6421271ec147e922a22c05ba24b11515e9aa6321",
    "swagger-ui-bundle.js": "62df541529080464a7660adc793eab7128c6193ce3be24ddc1e0e0a4a63edc2f",
    "swagger-ui-standalone-preset.js": "5243d492e14505e0cab87ac8b0195d0e615943e651743b2b698450a46eb470be",
    "LICENSE": "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30",
    "NOTICE": "0d20d1adef18aee3f40dd258172155521ce702ac445cb5f7b7d60ed32dad2fb2",
    "swagger-ui-bundle.js.LICENSE.txt": "63818894e4b04cd0e3180d9cb20761e227a939121e7484f8e1d528227c756f89",
    "swagger-ui-standalone-preset.js.LICENSE.txt": "000580e4e2255ea6ccde0c47f6d75e2f703a1931298fde58756793b67c0daed9",
}
REDOC_SOURCE_SHA256 = "dcaf76612bc4a3fbcc923a8966dee2f6146a5f32e5ce1b6f02dd60cbbf89500b"
REDOC_LOGO_URL = "https://cdn.redoc.ly/redoc/logo-mini.svg"
REDOC_LOGO_SHA256 = "1dab4315f8de2177b2b2726b29e84a26314c69cd27d692228947c0058793d5a7"
REDOC_SHA256 = {
    "redoc.standalone.js": "f6f01d44331204dfd1e0aef8c0caee9fe59d3edc7669447ec5d89bffd8f82110",
    "redoc-mark.svg": REDOC_LOGO_SHA256,
    "LICENSE": "d3026d549cf68ab7355bcfa85877bf8f845b3334a7efbfdc63936432fb34ff0e",
    "redoc.standalone.js.LICENSE.txt": "eed602ec32e00b2b9df1984fbcc26a687b1b3193ec01961389c4b8439e6edf73",
}
REDOC_ARCHIVE_MEMBERS = {
    "redoc.standalone.js": "package/bundles/redoc.standalone.js",
    "LICENSE": "package/LICENSE",
    "redoc.standalone.js.LICENSE.txt": "package/bundles/redoc.standalone.js.LICENSE.txt",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_swagger_inputs() -> dict[str, bytes]:
    lock = json.loads(LOCK.read_text())
    package = lock["packages"]["node_modules/swagger-ui-dist"]
    manifest = json.loads((ROOT / "frontend/package.json").read_text())
    if (
        manifest.get("scarfSettings") != {"enabled": False}
        or manifest["devDependencies"].get("swagger-ui-dist") != SWAGGER_VERSION
        or manifest["devDependencies"].get("@scarf/scarf") != "1.4.0"
        or package["version"] != SWAGGER_VERSION
        or package["integrity"] != SWAGGER_INTEGRITY
    ):
        raise ValueError("documentation_dependency_lock_changed")
    checked = {}
    for name, expected in APPROVED_SHA256.items():
        data = (PACKAGE / name).read_bytes()
        if digest(data) != expected:
            raise ValueError("swagger_asset_hash_changed")
        checked[name] = data
    return checked


def checked_redoc_archive(destination: Path) -> dict[str, bytes]:
    result = subprocess.run(
        [
            "npm", "pack", "redoc@2.5.4", "--ignore-scripts", "--json",
            "--pack-destination", str(destination),
        ],
        cwd=destination,
        capture_output=True,
        text=True,
        check=True,
    )
    records = json.loads(result.stdout)
    if len(records) != 1 or records[0]["name"] != "redoc" or records[0]["version"] != "2.5.4":
        raise ValueError("redoc_version_changed")
    archive_path = destination / records[0]["filename"]
    if digest(archive_path.read_bytes()) != REDOC_TARBALL_SHA256:
        raise ValueError("redoc_archive_hash_changed")
    output = {}
    with tarfile.open(archive_path, "r:gz") as archive:
        for name, member in REDOC_ARCHIVE_MEMBERS.items():
            source = archive.extractfile(member)
            if source is None:
                raise ValueError("redoc_asset_missing")
            output[name] = source.read()
    if digest(output["redoc.standalone.js"]) != REDOC_SOURCE_SHA256:
        raise ValueError("redoc_source_bundle_hash_changed")
    for name in ("LICENSE", "redoc.standalone.js.LICENSE.txt"):
        expected = REDOC_SHA256[name]
        if digest(output[name]) != expected:
            raise ValueError("redoc_asset_hash_changed")
    upstream = output["redoc.standalone.js"]
    if upstream.count(REDOC_LOGO_URL.encode("ascii")) != 1:
        raise ValueError("redoc_logo_reference_changed")
    output["redoc.standalone.js"] = upstream.replace(
        REDOC_LOGO_URL.encode("ascii"), b"/docs-assets/redoc/redoc-mark.svg"
    )
    with urllib.request.urlopen(REDOC_LOGO_URL, timeout=15) as response:
        logo = response.read(16 * 1024)
    if digest(logo) != REDOC_LOGO_SHA256 or not logo.startswith(b"<svg "):
        raise ValueError("redoc_logo_hash_changed")
    output["redoc-mark.svg"] = logo
    for name, expected in REDOC_SHA256.items():
        if digest(output[name]) != expected:
            raise ValueError("redoc_derived_asset_hash_changed")
    return output


def verify_vendored(swagger: dict[str, bytes]) -> None:
    for name, data in swagger.items():
        if (DEST / "swagger" / name).read_bytes() != data:
            raise ValueError("vendored_swagger_changed")
    for name, expected in REDOC_SHA256.items():
        if digest((DEST / "redoc" / name).read_bytes()) != expected:
            raise ValueError("vendored_redoc_changed")


def main() -> int:
    if sys.argv[1:] not in (["--write"], ["--check"]):
        print("usage: docs_assets.py --write|--check")
        return 2
    try:
        swagger = checked_swagger_inputs()
        if sys.argv[1] == "--write":
            with tempfile.TemporaryDirectory(prefix="agentmonitor-redoc-") as temp:
                redoc = checked_redoc_archive(Path(temp))
            (DEST / "swagger").mkdir(parents=True, exist_ok=True)
            (DEST / "redoc").mkdir(parents=True, exist_ok=True)
            for name, data in swagger.items():
                (DEST / "swagger" / name).write_bytes(data)
            for name, data in redoc.items():
                (DEST / "redoc" / name).write_bytes(data)
        verify_vendored(swagger)
    except (OSError, KeyError, ValueError, subprocess.CalledProcessError) as error:
        print(f"DOCS ASSETS: FAILED — {type(error).__name__}")
        return 1
    print("DOCS ASSETS: PASSED exact locked hashes and preserved notices")
    return 0


if __name__ == "__main__":
    sys.exit(main())
