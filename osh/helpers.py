#!/usr/bin/env python3
import ast
import contextlib
import os
from pathlib import Path

import libcst as cst

from osh.compat import Optional, Union
from osh.exceptions import NoManifestFound
from osh.settings import MANIFEST_NAMES
from osh.utils import parse_repository_url


def ask(prompt: str, default="y"):
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        answer = ""
    return answer or default


def ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def is_dir_empty(p: Path) -> bool:
    try:
        return p.is_dir() and not any(p.iterdir())
    except FileNotFoundError:
        return False


def rewrite_symlink(link: Path, old_prefix: str, new_prefix: str):
    try:
        target = os.readlink(link)
    except OSError:
        return False
    if old_prefix in target:
        new_target = target.replace(old_prefix, new_prefix)
        link.unlink()
        os.symlink(new_target, link)
        return True
    return False


def desired_path(url: str, base_dir: str, pull_request: bool = False) -> str:
    _, owner, repo = parse_repository_url(url)
    if owner == "oca":
        owner = owner.upper()

    if pull_request:
        return f"{base_dir.rstrip('/')}/PRs/{owner}/{repo}"

    return f"{base_dir.rstrip('/')}/{owner}/{repo}"


def symlink_targets(repo: Path):
    targets = []
    for root, dirs, files in os.walk(repo):
        if ".git" in dirs:
            dirs.remove(".git")
        for n in dirs + files:
            p = Path(root) / n
            if p.is_symlink():
                with contextlib.suppress(OSError):
                    targets.append(os.readlink(p))

    return targets


def relpath(from_path: Path, to_path: Path) -> str:
    return os.path.relpath(to_path, start=from_path)


def find_addons(root: Path, shallow: bool = False):
    root_parts = root.resolve().parts

    # followlinks=True lets us enter first-level *symlinked* directories
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        # skip VCS noise
        if ".git" in dirnames:
            dirnames.remove(".git")

        # found an addon here?
        if "__manifest__.py" in filenames or "__openerp__.py" in filenames:
            yield Path(dirpath)

        if shallow:
            depth = len(Path(dirpath).resolve().parts) - len(root_parts)
            if depth >= 1:
                # we're already in a first-level subdir (real or symlink) → don't go deeper
                dirnames[:] = []


def get_manifest_path(addon_dir):
    for manifest_name in MANIFEST_NAMES:
        manifest_path = os.path.join(addon_dir, manifest_name)
        if os.path.isfile(manifest_path):
            return manifest_path


def parse_manifest(raw: str) -> dict:
    return ast.literal_eval(raw)


def parse_manifest_cst(raw: str) -> cst.CSTNode:
    return cst.parse_module(raw)


def read_manifest(path: str) -> cst.CSTNode:
    manifest_path = get_manifest_path(path)
    if not manifest_path:
        raise NoManifestFound(f"no Odoo manifest found in {path}")
    with open(manifest_path) as mf:
        return parse_manifest_cst(mf.read())


def load_manifest(path: Path) -> dict:
    """
    Parse an Odoo manifest file,
    then safely convert it to a Python dict via ast.literal_eval.
    """
    source = path.read_text(encoding="utf-8")

    # Convert the exact dict literal slice to a Python object (safe: literals only).
    manifest = ast.literal_eval(source)
    if not isinstance(manifest, dict):
        raise ValueError("Parsed manifest is not a dict after literal evaluation.")
    return manifest


def find_addons_extended(
    addons_dir: Union[str, Path], installable_only: bool = False, names: Optional[list] = None
):
    """yield (addon_name, addon_dir, manifest)"""
    for name in os.listdir(addons_dir):
        path = os.path.join(addons_dir, name)
        try:
            manifest = parse_manifest(path)
        except NoManifestFound:
            continue
        if installable_only and not manifest.get("installable", True):
            continue

        if names and name not in names:
            continue

        yield name, path, manifest


def find_manifests(path: str, names: Optional[list] = None):
    for name in os.listdir(path):
        addon_path = os.path.join(path, name)
        try:
            manifest_path = get_manifest_path(addon_path)
        except NoManifestFound:
            continue

        if names and name not in names:
            continue

        yield manifest_path
