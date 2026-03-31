#!/usr/bin/env python3
"""Interactive installer for odoo-manager."""

import os
import re
import stat
import sys
from pathlib import Path

HOME = Path.home()
SCRIPTS_DIR = Path(__file__).parent.resolve()
MARKER = "# odoo-manager"
VERSION_RE = re.compile(r'^(master|(saas-)?[0-9]{2}\.[0-9])$')

DRY_RUN = "--dry-run" in sys.argv


def find_versions(src_path):
    """Return sorted list of Odoo version dirs found inside src_path."""
    p = Path(src_path)
    if not p.is_dir():
        return []
    return sorted(
        d.name for d in p.iterdir()
        if d.is_dir() and VERSION_RE.match(d.name)
    )


def ask(prompt, default=None):
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
    answer = input(full_prompt).strip()
    return answer if answer else default


def ask_choice(prompt, choices, default=None):
    options = "/".join(
        c.upper() if c == default else c for c in choices
    )
    while True:
        answer = input(f"{prompt} [{options}]: ").strip().lower()
        if not answer and default:
            return default
        if answer in choices:
            return answer
        print(f"  Please enter one of: {', '.join(choices)}")


def detect_shell_config():
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        return str(HOME / ".zshrc")
    return str(HOME / ".bashrc")


def idempotent_append(path, block):
    """Append block to file only if MARKER is not already present."""
    p = Path(path)
    if p.exists() and MARKER in p.read_text():
        print(f"  Already configured in {path}, skipping.")
        return
    if DRY_RUN:
        print(f"  Would append to {path}")
        return
    with open(path, "a") as f:
        f.write(f"\n{block}\n")
    print(f"  Updated {path}")


def write_odoorc(path, db_name="odoo"):
    p = Path(path)
    if p.exists():
        print(f"  {path} already exists, skipping.")
        return
    if DRY_RUN:
        print(f"  Would create {path}")
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        f"[options]\n"
        f"db_name = {db_name}\n"
    )
    print(f"  Created {path}")


def ensure_executable():
    """Make sure all scripts in SCRIPTS_DIR have the executable bit set."""
    fixed = []
    for f in SCRIPTS_DIR.iterdir():
        if not f.is_file():
            continue
        try:
            first = f.open("rb").read(2)
        except OSError:
            continue
        if first != b"#!":
            continue
        current = f.stat().st_mode
        desired = current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        if current != desired:
            if not DRY_RUN:
                f.chmod(desired)
            fixed.append(f.name)
    if fixed:
        verb = "Would set" if DRY_RUN else "Set"
        print(f"  {verb} +x on: {', '.join(sorted(fixed))}")
    else:
        print("  All scripts already executable.")



def write_conf(src_path, env_path):
    conf_path = HOME / ".odoo-manager.conf"
    if DRY_RUN:
        print(f"  Would write {conf_path}")
        return
    conf_path.write_text(
        f"# odoo-manager configuration — sourced by install.py\n"
        f"export ODOO_SRC_PATH={src_path}\n"
        f"export ODOO_ENV_PATH={env_path}\n"
    )
    print(f"  Written {conf_path}")


def main():
    if DRY_RUN:
        print("=== odoo-manager installer (dry run — nothing will be written) ===\n")
    else:
        print("=== odoo-manager installer ===\n")

    setup_mode = ask_choice(
        "Setup mode — single ~/.odoorc or multi (per-version ~/src/<ver>/.odoorc)",
        choices=["single", "multi"],
        default="single",
    )

    default_src = str(HOME / "src")
    src_path = ask("Odoo source base path", default=default_src)

    default_env = str(HOME / "odoo-env")
    env_path = ask("Odoo virtualenv base path", default=default_env)

    default_rc = detect_shell_config()
    shell_rc = ask("Shell config file to update", default=default_rc)

    print()

    ensure_executable()
    write_conf(src_path, env_path)

    if setup_mode == "single":
        write_odoorc(HOME / ".odoorc")
    else:
        versions = find_versions(src_path)
        if versions:
            print(f"  Found versions in {src_path}: {', '.join(versions)}")
        else:
            print(f"  No version directories found in {src_path}")
        for ver in versions:
            write_odoorc(Path(src_path) / ver / ".odoorc")
        # Also create ~/.odoorc as a fallback if absent
        write_odoorc(HOME / ".odoorc")

    shell_block = (
        f"{MARKER}\n"
        f'export PATH="{SCRIPTS_DIR}:$PATH"\n'
        f'[ -f "$HOME/.odoo-manager.conf" ] && source "$HOME/.odoo-manager.conf"\n'
        f'[ -f "{SCRIPTS_DIR}/.bash_completion" ] && source "{SCRIPTS_DIR}/.bash_completion"'
    )
    idempotent_append(shell_rc, shell_block)

    print()
    print("Done. Open a new shell (or run `source " + shell_rc + "`) to apply changes.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
