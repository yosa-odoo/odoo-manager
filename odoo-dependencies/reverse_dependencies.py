#!/usr/bin/env python3
"""Recursively list all modules that depend on a given Odoo module."""

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


def parse_deps(manifest_path):
    try:
        data = ast.literal_eval(manifest_path.read_text(encoding="utf-8"))
        return data.get("depends", [])
    except (SyntaxError, ValueError):
        print(f"Warning: could not parse {manifest_path}")
        return []


def build_reverse_map(dirs):
    reverse_map = {}
    for d in dirs:
        for module_dir in d.iterdir():
            manifest = module_dir / "__manifest__.py"
            if not manifest.exists():
                continue
            for dep in parse_deps(manifest):
                reverse_map.setdefault(dep, set()).add(module_dir.name)
    return reverse_map


def crawl(module, reverse_map, visited=None):
    if visited is None:
        visited = set()
    if module in visited:
        return visited
    visited.add(module)
    for dependent in reverse_map.get(module, []):
        crawl(dependent, reverse_map, visited)
    return visited


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List all modules that depend on an Odoo module.")
    parser.add_argument("module", help="Module name")
    parser.add_argument("-o", "--version", help="Odoo version (e.g. 17.0)")
    args = parser.parse_args()

    src = get_src(args.version)
    dirs = base_dirs(src)
    reverse_map = build_reverse_map(dirs)
    dependents = crawl(args.module, reverse_map)
    dependents.discard(args.module)

    for dep in sorted(dependents):
        print(dep)
