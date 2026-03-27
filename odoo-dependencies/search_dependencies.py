#!/usr/bin/env python3
"""Recursively list all dependencies of an Odoo module."""

import ast
import os
import argparse
from pathlib import Path


def get_src(version=None):
    if not version:
        version = os.environ.get("OVERSION")
    if not version:
        version_file = Path.home() / ".odoo_current_version"
        if version_file.exists():
            version = version_file.read_text().strip()
    if not version:
        raise SystemExit("No Odoo version found. Use -o VERSION or run b/setdb first.")
    return Path.home() / "src" / version


def base_dirs(src):
    candidates = [
        src / "odoo" / "addons",
        src / "odoo" / "odoo" / "addons",
        src / "enterprise",
        src / "custom",
    ]
    return [d for d in candidates if d.is_dir()]


def get_manifest(module, dirs):
    for d in dirs:
        path = d / module / "__manifest__.py"
        if path.exists():
            return path
    return None


def parse_deps(manifest_path):
    try:
        data = ast.literal_eval(manifest_path.read_text(encoding="utf-8"))
        return data.get("depends", [])
    except (SyntaxError, ValueError):
        print(f"Warning: could not parse {manifest_path}")
        return []


def crawl(module, dirs, visited=None):
    if visited is None:
        visited = set()
    if module in visited:
        return visited
    manifest = get_manifest(module, dirs)
    if not manifest:
        print(f"Warning: module '{module}' not found")
        return visited
    visited.add(module)
    for dep in parse_deps(manifest):
        crawl(dep, dirs, visited)
    return visited


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List all dependencies of an Odoo module.")
    parser.add_argument("module", help="Module name")
    parser.add_argument("-o", "--version", help="Odoo version (e.g. 17.0)")
    args = parser.parse_args()

    src = get_src(args.version)
    dirs = base_dirs(src)
    deps = crawl(args.module, dirs)
    deps.discard(args.module)

    for dep in sorted(deps):
        print(dep)
