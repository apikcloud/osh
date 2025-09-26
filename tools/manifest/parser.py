#!/usr/bin/env python3

"""
Apply opinionated fixes to Odoo manifest files using LibCST
while preserving inline comments and original formatting.

Self‑contained version (no external helpers).

Main features
-------------
- Rename misspelled maintainer keys -> "maintainers".
- Normalize maintainers values (string -> list, apply replacements).
- Force canonical values for some keys (author, website, license).
- Trim summary; if description exists and summary is missing, move description into summary, then drop description.
- Sort depends alphabetically with "base" first.
- Ensure a set of default keys exist (without overwriting existing ones).
- Optionally inject standard header comments if missing.
- Preserves comments and whitespace thanks to LibCST (no black round‑trip).

CLI
---
    python fix_manifest_libcst.py --addons-dir . [--dry] [--check]
    python fix_manifest_libcst.py --manifest-path path/to/__manifest__.py

- --dry : do not write files (preview changes)
- --check : exit 1 if any file would change (useful for pre-commit)
- --no-inject-headers : do not prepend the header comments

Tested with Python 3.12 and LibCST >= 1.2.
"""

from __future__ import annotations

import ast
import os
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import click
import libcst as cst
from libcst import CSTTransformer, RemovalSentinel
from libcst.metadata import ParentNodeProvider

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
MANIFEST_NAMES = ("__manifest__.py", "__openerp__.py", "__terp__.py")
EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
}

REPLACEMENTS: Dict[str, str] = {
    "Frederic Grall": "fredericgrall",
    "Michel GUIHENEUF": "apik-mgu",
    "rth-apik": "Romathi",
    "Romain THIEUW": "Romathi",
    "Aurelien ROY": "royaurelien",
}

FORCED_KEYS = {
    "author": "Apik",
    "website": "https://apik.cloud",
    "license": "LGPL-3",
}

DEFAULT_VALUES = {
    "category": "Technical",
    "maintainers": [],
    "depends": [],
    "data": [],
    "demo": [],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}

HEADERS = [
    "# pylint: disable=W0104",
    "# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).",
]

MISSPELLED_MAINTAINERS = {"mainteners", "maintener", "maintainer"}

# ---------------------------------------------------------------------------
# Utilities over CST nodes
# ---------------------------------------------------------------------------


def _string_value(s: cst.SimpleString) -> str:
    """Return the unquoted Python value of a SimpleString using ast.literal_eval."""
    try:
        # LibCST keeps the raw token including quotes; literal_eval is safe here
        return ast.literal_eval(s.value)
    except Exception:
        v = s.value
        return v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'") else v


def _make_str(value: str, like: Optional[cst.SimpleString] = None) -> cst.SimpleString:
    """Create a SimpleString preserving quote style if a reference string is provided."""
    if like is not None and len(like.value) >= 1 and like.value[0] in ('"', '"'):
        q = like.value[0]
        return cst.SimpleString(f"{q}{value}{q}")
    return cst.SimpleString(repr(value))


def _normalize_list_of_strings(
    node: cst.BaseExpression, replacements: Dict[str, str]
) -> cst.BaseExpression:
    """If node is a string -> wrap into list; if list/tuple of strings -> map replacements."""
    if isinstance(node, cst.SimpleString):
        old = _string_value(node)
        new = replacements.get(old, old)
        return cst.List([cst.Element(value=_make_str(new, like=node))])

    if isinstance(node, (cst.List, cst.Tuple)):
        new_elements: List[cst.Element] = []
        changed = False
        for el in node.elements:
            if el is None or el.value is None:
                new_elements.append(el)
                continue
            v = el.value
            if isinstance(v, cst.SimpleString):
                old = _string_value(v)
                new = replacements.get(old, old)
                if new != old:
                    changed = True
                    v = _make_str(new, like=v)
                new_elements.append(el.with_changes(value=v))
            else:
                new_elements.append(el)
        return node.with_changes(elements=new_elements) if changed else node

    return node


def _sort_depends(node: cst.BaseExpression) -> cst.BaseExpression:
    if not isinstance(node, (cst.List, cst.Tuple)):
        return node

    values: List[Tuple[str, cst.Element]] = []
    for el in node.elements:
        if el is None or el.value is None:
            continue
        v = el.value
        if isinstance(v, cst.SimpleString):
            values.append((_string_value(v), el))

    if not values:
        return node

    # Sort alpha; ensure "base" first
    sorted_vals = sorted(values, key=lambda t: t[0])
    has_base = any(s == "base" for s, _ in values)
    if has_base:
        sorted_vals = [v for v in sorted_vals if v[0] == "base"] + [
            v for v in sorted_vals if v[0] != "base"
        ]

    new_elements: List[cst.Element] = [el for (_, el) in sorted_vals]
    return node.with_changes(elements=new_elements)


@dataclass
class KeyEdit:
    key_node: cst.BaseExpression
    value_node: cst.BaseExpression
    index: int


class ManifestTransformer(CSTTransformer):
    METADATA_DEPENDENCIES = (ParentNodeProvider,)

    def __init__(self) -> None:
        super().__init__()
        self._done = False
        self.changed = False

    def _ancestors(self, node: cst.CSTNode):
        cur = node
        while True:
            cur = self.get_metadata(ParentNodeProvider, cur, None)
            if cur is None:
                break
            yield cur

    # Only transform the first module-level dict (not inside def/class)
    def leave_Dict(self, original_node: cst.Dict, updated_node: cst.Dict) -> cst.BaseExpression:
        if self._done:
            return updated_node

        ancestors = list(self._ancestors(original_node))
        if not any(isinstance(a, cst.Module) for a in ancestors):
            return updated_node
        if any(isinstance(a, (cst.FunctionDef, cst.ClassDef)) for a in ancestors):
            return updated_node

        new_dict, changed = self._edit_manifest_dict(updated_node)
        if changed:
            self.changed = True
        self._done = True
        return new_dict

    # Core editing logic at Dict level
    def _edit_manifest_dict(self, node: cst.Dict):
        key_map: Dict[str, KeyEdit] = {}
        for idx, elem in enumerate(node.elements):
            if not isinstance(elem, cst.DictElement):
                continue
            key = elem.key
            if isinstance(key, cst.SimpleString):
                k = _string_value(key)
            else:
                continue
            key_map[k] = KeyEdit(key_node=key, value_node=elem.value, index=idx)

        changed = False
        elements: List[cst.BaseElement] = list(node.elements)

        def update_value_at(key: str, new_value: cst.BaseExpression) -> None:
            nonlocal changed
            if key in key_map:
                idx = key_map[key].index
                old_elem = elements[idx]
                if isinstance(old_elem, cst.DictElement):
                    elements[idx] = old_elem.with_changes(value=new_value)
                    changed = True

        def rename_key(old_key: str, new_key: str) -> None:
            nonlocal changed
            if old_key in key_map:
                idx = key_map[old_key].index
                old_elem = elements[idx]
                if isinstance(old_elem, cst.DictElement):
                    like = key_map[old_key].key_node
                    elements[idx] = old_elem.with_changes(key=_make_str(new_key, like=like))
                    changed = True

        def ensure_key(key: str, value: cst.BaseExpression) -> None:
            nonlocal changed
            if key in key_map:
                return
            elements.append(cst.DictElement(key=cst.SimpleString(repr(key)), value=value))
            changed = True

        # 1) Rename misspelled maintainer keys
        for wrong in MISSPELLED_MAINTAINERS:
            if wrong in key_map:
                rename_key(wrong, "maintainers")
                key_map["maintainers"] = key_map.pop(wrong)

        # 2) Normalize maintainers
        if "maintainers" in key_map:
            val = key_map["maintainers"].value_node
            new_val = _normalize_list_of_strings(val, REPLACEMENTS)
            if new_val is not val:
                update_value_at("maintainers", new_val)
        # Derive from author if contains "michel" (example heuristic)
        elif "author" in key_map:
            author_node = key_map["author"].value_node
            if (
                isinstance(author_node, cst.SimpleString)
                and "michel" in _string_value(author_node).lower()
            ):
                ensure_key(
                    "maintainers",
                    cst.List([cst.Element(value=_make_str(REPLACEMENTS["Michel GUIHENEUF"]))]),
                )

        # 3) Force canonical values
        for k, v in FORCED_KEYS.items():
            if k in key_map:
                cur = key_map[k].value_node
                if not (isinstance(cur, cst.SimpleString) and _string_value(cur) == v):
                    update_value_at(
                        k,
                        _make_str(v, like=cur if isinstance(cur, cst.SimpleString) else None),
                    )
            else:
                ensure_key(k, _make_str(v))

        # 4) Summary and description
        if "summary" in key_map:
            cur = key_map["summary"].value_node
            if isinstance(cur, cst.SimpleString):
                stripped = _string_value(cur).strip()
                if stripped != _string_value(cur):
                    update_value_at("summary", _make_str(stripped, like=cur))
        if "description" in key_map:
            desc_node = key_map["description"].value_node
            if isinstance(desc_node, cst.SimpleString):
                desc_text = _string_value(desc_node).strip()
                if "summary" not in key_map and desc_text:
                    ensure_key("summary", _make_str(desc_text, like=desc_node))
            idx = key_map["description"].index
            el = elements[idx]
            if isinstance(el, cst.DictElement):
                elements[idx] = RemovalSentinel.REMOVE
                changed = True

        # 5) Defaults
        for k, v in DEFAULT_VALUES.items():
            if k not in key_map:
                ensure_key(k, cst.parse_expression(repr(v)))

        # 6) depends sorting
        if "depends" in key_map:
            val = key_map["depends"].value_node
            new_val = _sort_depends(val)
            if new_val is not val:
                update_value_at("depends", new_val)

        # Rebuild (skip removals)
        new_elements: List[cst.DictElement] = []
        for el in elements:
            if el is RemovalSentinel.REMOVE:
                continue
            if isinstance(el, cst.DictElement):
                new_elements.append(el)

        return node.with_changes(elements=new_elements), changed


# ---------------------------------------------------------------------------
# Helpers: header injection
# ---------------------------------------------------------------------------


def ensure_headers(text: str) -> str:
    lines = text.splitlines()
    non_empty = [l for l in lines if l.strip()]
    if (
        len(non_empty) >= 2
        and non_empty[0].strip() == HEADERS[0]
        and non_empty[1].strip() == HEADERS[1]
    ):
        return text
    head = "\n".join(HEADERS)
    body = text if text.endswith("\n") else text + "\n"
    return head + "\n" + body


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------


def iter_manifest_files(root: str) -> Iterable[Tuple[str, str]]:
    """Yield (addon_name, manifest_path) for any directory containing a manifest file."""
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        # prune
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for mf in MANIFEST_NAMES:
            if mf in filenames:
                addon = os.path.basename(dirpath)
                yield addon, os.path.join(dirpath, mf)
                break


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.command(name="parser")
@click.option(
    "--addons-dir",
    default=".",
    show_default=True,
    help="Root directory to scan for addons.",
)
@click.option(
    "--manifest-path",
    type=click.Path(exists=True, dir_okay=False),
    help="Operate on a single manifest file.",
)
@click.option(
    "--inject-headers/--no-inject-headers",
    default=True,
    show_default=True,
    help="Prepend standard header comments if missing.",
)
@click.option(
    "--dry/--write",
    default=False,
    show_default=True,
    help="Dry-run: show what would change without writing.",
)
@click.option(
    "--check/--no-check",
    default=False,
    show_default=True,
    help="Exit 1 if any file would change (useful in CI/pre-commit).",
)
@click.option("--verbose/--quiet", default=True, show_default=True)
def main(  # noqa: C901, PLR0912, PLR0913
    addons_dir: str,
    inject_headers: bool,
    dry: bool,
    check: bool,
    verbose: bool,
    manifest_path: Optional[str] = None,
) -> None:
    targets: list[tuple[str, str]] = []

    if manifest_path:
        targets.append((os.path.basename(os.path.dirname(manifest_path)), manifest_path))
    else:
        targets.extend(iter_manifest_files(addons_dir))

    if not targets:
        if verbose:
            click.echo("No manifest files found.")
        sys.exit(0)

    total = 0
    changed_count = 0

    for name, path in targets:
        try:
            with open(path, encoding="utf-8") as f:
                original = f.read()
            module = cst.parse_module(original)
            wrapper = cst.MetadataWrapper(module)
            transformer = ManifestTransformer()
            new_module = wrapper.visit(transformer)
            new_code = new_module.code
            if inject_headers:
                new_code = ensure_headers(new_code)
        except Exception as e:
            click.echo(f"⚠️  Skip {name}: {path}: parse/transform error: {e}")
            continue

        total += 1
        if transformer.changed or new_code != original:
            changed_count += 1
            if verbose:
                click.echo(f"✅ Edited {name} : {path}")
            if not dry:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_code)
        elif verbose:
            click.echo(f"➡️  No change {name} : {path}")

    if verbose:
        click.echo(f"Done. {changed_count}/{total} manifest(s) changed.")

    if check and changed_count > 0:
        sys.exit(1)
