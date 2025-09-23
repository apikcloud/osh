#!/usr/bin/env python3

import os

import black
import click
from libcst.display import dump

from tools.manifest import find_addons, get_manifest_path

MANIFEST_NAMES = ("__manifest__.py", "__openerp__.py", "__terp__.py")

BLACK_MODE = black.FileMode()
REPLACEMENTS = {
    "Frederic Grall": "fredericgrall",
    "Michel GUIHENEUF": "apik-mgu",
    "rth-apik": "Romathi",
    "Romain THIEUW": "Romathi",
    "Aurelien ROY": "royaurelien",
}


FORCED_KEYS = ["author", "website", "license"]

HEADERS = [
    "# pylint: disable=W0104",
    "# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).",
]

DEFAULT_VALUES = {
    "name": None,
    "summary": None,
    "category": "Technical",
    "author": "Apik",
    "maintainers": [],
    "website": "https://apik.cloud",
    "version": None,
    "license": "LGPL-3",
    "depends": [],
    "data": [],
    "demo": [],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}


def format_manifest(data: dict) -> str:
    raw = "\n".join(HEADERS) + "\n" + repr(data)
    return black.format_str(raw, mode=BLACK_MODE)


def process_manifest(manifest: str, force_default: bool = True):
    changed = False

    for key in ["mainteners", "maintener", "maintainer"]:
        if key in manifest:
            manifest["maintainers"] = manifest.pop(key)
            changed = True
            continue

    for key in ["maintainers"]:
        if key in manifest:
            val = manifest[key]

            if isinstance(val, str) and val in REPLACEMENTS:
                manifest[key] = [REPLACEMENTS[val]]
                changed = True
            elif isinstance(val, (list, tuple)):
                new_val = [REPLACEMENTS.get(v, v) for v in val]
                if new_val != val:
                    manifest[key] = new_val
                    changed = True
        elif "michel" in manifest["author"].lower():
            manifest[key] = [REPLACEMENTS["Michel GUIHENEUF"]]
            changed = True

    for key in FORCED_KEYS:
        if manifest.get(key) != DEFAULT_VALUES[key]:
            manifest[key] = DEFAULT_VALUES[key]
            changed = True

    # Cleaning up summary
    if summary := manifest.get("summary"):
        manifest["summary"] = summary.strip().rstrip()
        changed = True

    # Remove description
    if desc := manifest.get("description"):
        if desc:
            manifest.pop("description")
            changed = True
            if "summary" not in manifest:
                manifest["summary"] = desc.strip().rstrip()
                changed = True

    manifest["depends"].sort()
    if "base" in manifest["depends"]:
        manifest["depends"].pop(manifest["depends"].index("base"))
        manifest["depends"].insert(0, "base")

    if force_default:
        res = {
            key: manifest.pop(key) if key in manifest and manifest.get(key) else value
            for key, value in DEFAULT_VALUES.items()
        }
        return True, res

    return changed, manifest


def save_mannifest(content: str, filepath: str) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        output = format_manifest(content)
        f.write(output)


@click.command()
@click.option("--addons-dir", default=".")
def main(addons_dir):
    for name, path, manifest in find_addons(addons_dir):
        print(name)
        if name == "apik_data":
            print(dump(manifest))
            print(manifest.code)
            return

        continue

        changed, manifest = process_manifest(manifest)

        if changed:
            filepath = os.path.join(addons_dir, get_manifest_path(name))
            save_mannifest(manifest, filepath)
            print(f"✅ Edited {name} : {filepath}")


if __name__ == "__main__":
    pass
