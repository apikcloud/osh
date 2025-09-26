#!/usr/bin/env python3
import ast
import contextlib
import os
from pathlib import Path

import libcst as cst

from tools.exceptions import NoManifestFound
from tools.settings import MANIFEST_NAMES
from tools.utils import parse_repository_url


def ask(prompt: str, default="y"):
    try:
        ans = input(prompt).strip().lower()
    except EOFError:
        ans = ""
    return ans or default


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


def desired_path(url: str, base_dir: str):
    _, owner, repo = parse_repository_url(url)
    if owner == "oca":
        owner = owner.upper()
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


def find_addons(root: Path):
    """Yield addon dirs under root (contain __manifest__.py or __openerp__.py)."""
    for dirpath, dirnames, filenames in os.walk(root):
        # skip VCS noise
        if ".git" in dirnames:
            dirnames.remove(".git")
        if "__manifest__.py" in filenames or "__openerp__.py" in filenames:
            yield Path(dirpath)


def get_manifest_path(addon_dir):
    for manifest_name in MANIFEST_NAMES:
        manifest_path = os.path.join(addon_dir, manifest_name)
        if os.path.isfile(manifest_path):
            return manifest_path


def parse_manifest(raw: str) -> dict:
    return ast.literal_eval(raw)


def parse_manifest_cst(raw: str) -> cst.CSTNode:
    return cst.parse_module(raw)


def read_manifest(path: str) -> dict:
    manifest_path = get_manifest_path(path)
    if not manifest_path:
        raise NoManifestFound(f"no Odoo manifest found in {path}")
    with open(manifest_path) as mf:
        return parse_manifest(mf.read())


def find_addons_extended(addons_dir: str, installable_only: bool = False):
    """yield (addon_name, addon_dir, manifest)"""
    for name in os.listdir(addons_dir):
        path = os.path.join(addons_dir, name)
        try:
            manifest = read_manifest(path)
        except NoManifestFound:
            continue
        if installable_only and not manifest.get("installable", True):
            continue
        yield name, path, manifest
