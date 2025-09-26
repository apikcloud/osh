#!/usr/bin/env python3
import ast
import contextlib
import logging
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import libcst as cst

from tools.compat import Optional, Union
from tools.exceptions import NoManifestFound

MANIFEST_NAMES = ("__manifest__.py", "__openerp__.py", "__terp__.py")


def run(
    cmd: list,
    check: bool = True,
    capture: bool = False,
    cwd: Optional[str] = None,
    name: Optional[str] = None,
) -> Union[str, None]:
    kwargs = dict(text=True, cwd=cwd)
    if capture:
        kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    logging.debug(f"[{name or 'run'}] {' '.join(cmd)}")

    res = subprocess.run(cmd, check=check, **kwargs)
    return res.stdout if capture else None


def parse_org_repo_from_url(url: str):
    # https://host/org/repo(.git), git@host:org/repo(.git), ssh://git@host/org/repo(.git)
    if re.match(r"^[\w.-]+@[\w.-]+:", url):
        host_path = url.split(":", 1)[1]
        parts = host_path.strip("/").split("/")
    else:
        u = urlparse(url)
        parts = u.path.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse org/repo from URL: {url}")
    org, repo = parts[-2], parts[-1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return org, repo


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
    org, repo = parse_org_repo_from_url(url)
    if org == "oca":
        org = org.upper()
    return f"{base_dir.rstrip('/')}/{org}/{repo}"


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


def parse_manifest(s):
    return cst.parse_module(s)
    return ast.literal_eval(s)


def read_manifest(addon_dir):
    manifest_path = get_manifest_path(addon_dir)
    if not manifest_path:
        raise NoManifestFound(f"no Odoo manifest found in {addon_dir}")
    with open(manifest_path) as mf:
        return parse_manifest(mf.read())


def find_addons_extended(addons_dir, installable_only=True):
    """yield (addon_name, addon_dir, manifest)"""
    for addon_name in os.listdir(addons_dir):
        addon_dir = os.path.join(addons_dir, addon_name)
        try:
            manifest = read_manifest(addon_dir)
        except NoManifestFound:
            continue
        # if installable_only and not manifest.get("installable", True):
        #     continue
        yield addon_name, addon_dir, manifest


def str_to_list(raw: str, sep=",") -> list:
    if not raw:
        return []
    return [item.strip().rstrip() for item in raw.split(sep)]
