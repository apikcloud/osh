#!/usr/bin/env python3
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse


def run(cmd, check=True, capture=False, cwd=None):
    kwargs = dict(text=True, cwd=cwd)
    if capture:
        kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
