#!/usr/bin/env python3
"""Interactive installer for odoo-manager."""

import os
import re
import stat
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
SCRIPTS_DIR = Path(__file__).parent.resolve()
MARKER = "# odoo-manager"
VERSION_RE = re.compile(r'^(master|(saas-)?[0-9]{2}\.[0-9])$')

DRY_RUN = "--dry-run" in sys.argv

ODOO_REPOS = {
    "odoo": {
        "origin": "git@github.com:odoo/odoo.git",
        "dev": "git@github.com:odoo-dev/odoo.git",
    },
    "enterprise": {
        "origin": "git@github.com:odoo/enterprise.git",
        "dev": "git@github.com:odoo-dev/enterprise.git",
    },
}


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


def ask_yes_no(prompt, default="yes"):
    choice = ask_choice(prompt, choices=["yes", "no"], default=default)
    return choice == "yes"


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


def run(cmd, cwd=None, env=None):
    """Print and run a command. Exit on failure."""
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    if DRY_RUN:
        return
    result = subprocess.run(cmd, cwd=cwd, env=env)
    if result.returncode != 0:
        print(f"  ERROR: command failed (exit {result.returncode})")
        sys.exit(result.returncode)


def git_has_remote(repo_dir, remote_name):
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "remote"],
        capture_output=True, text=True,
    )
    return remote_name in result.stdout.splitlines()


def clone_repos(src_path):
    """Clone odoo and enterprise into <src_path>/master/ and set up remotes."""
    master_dir = Path(src_path) / "master"
    print(f"\nCloning Odoo repositories into {master_dir}...")
    if not DRY_RUN:
        master_dir.mkdir(parents=True, exist_ok=True)

    for repo, urls in ODOO_REPOS.items():
        repo_dir = master_dir / repo
        if repo_dir.exists():
            print(f"  {repo_dir} already exists, skipping clone.")
        else:
            run(["git", "clone", urls["origin"], str(repo_dir)])

        if not DRY_RUN and git_has_remote(repo_dir, "dev"):
            print(f"  [{repo}] Remote 'dev' already exists, skipping.")
        else:
            run(["git", "-C", str(repo_dir), "remote", "add", "dev", urls["dev"]])

        run([
            "git", "-C", str(repo_dir),
            "remote", "set-url", "--push", "origin",
            "you_should_not_push_on_this_repository",
        ])


def create_master_venv(src_path, env_path):
    """Create Python virtualenv for master and install requirements."""
    venv_dir = Path(env_path) / "master"
    req_file = Path(src_path) / "master" / "odoo" / "requirements.txt"
    print(f"\nCreating Python virtualenv for master at {venv_dir}...")

    if not DRY_RUN and venv_dir.exists():
        print(f"  {venv_dir} already exists, skipping.")
        return

    if not DRY_RUN:
        Path(env_path).mkdir(parents=True, exist_ok=True)

    use_uv = subprocess.run(["which", "uv"], capture_output=True).returncode == 0
    if use_uv:
        run(["uv", "venv", "--python", "3.12", str(venv_dir)])
        run(["uv", "pip", "install", "-q",
             "--python", str(venv_dir / "bin" / "python"),
             "-r", str(req_file)])
    else:
        run(["python3", "-m", "venv", str(venv_dir)])
        run([str(venv_dir / "bin" / "pip"), "install", "-q",
             "-r", str(req_file)])

    print(f"  Done: {venv_dir}")


def setup_extra_versions(src_path, env_path, versions):
    """Call new-odoo-version for each requested version."""
    if not versions:
        return
    script = SCRIPTS_DIR / "new-odoo-version"
    env = os.environ.copy()
    env["ODOO_SRC_PATH"] = str(src_path)
    env["ODOO_ENV_PATH"] = str(env_path)
    print(f"\nSetting up extra versions: {', '.join(versions)}...")
    run([str(script)] + versions, env=env)


def ensure_dirs(src_path, env_path):
    """Check that src/env dirs exist; offer to create any that are missing."""
    missing = [p for p in [src_path, env_path] if not Path(p).is_dir()]
    if not missing:
        return
    print("\n  Warning: the following directories do not exist:")
    for p in missing:
        print(f"    {p}")
    if ask_yes_no("  Create them now?", default="yes"):
        for p in missing:
            if DRY_RUN:
                print(f"  Would create {p}")
            else:
                Path(p).mkdir(parents=True, exist_ok=True)
                print(f"  Created {p}")
    else:
        print("  Proceeding without creating directories.")


def main():
    if DRY_RUN:
        print("=== odoo-manager installer (dry run — nothing will be written) ===\n")
    else:
        print("=== odoo-manager installer ===\n")

    already_cloned = ask_yes_no(
        "Is Odoo/enterprise already cloned on this machine?",
        default="yes",
    )

    default_src = str(HOME / "src")
    src_path = ask("Odoo source base path", default=default_src)

    default_env = str(HOME / "odoo-env")
    env_path = ask("Odoo virtualenv base path", default=default_env)

    if not already_cloned:
        if DRY_RUN:
            print(f"  Would create {src_path} and {env_path}")
        else:
            Path(src_path).mkdir(parents=True, exist_ok=True)
            Path(env_path).mkdir(parents=True, exist_ok=True)
    else:
        ensure_dirs(src_path, env_path)

    setup_mode = ask_choice(
        "\nSetup mode — single ~/.odoorc or multi (per-version <src>/<ver>/.odoorc)",
        choices=["single", "multi"],
        default="single",
    )

    default_rc = detect_shell_config()
    shell_rc = ask("Shell config file to update", default=default_rc)

    print()
    ensure_executable()
    write_conf(src_path, env_path)

    if not already_cloned:
        clone_repos(src_path)
        create_master_venv(src_path, env_path)

        print()
        versions_input = ask(
            "Additional versions to set up (space-separated, e.g. '17.0 18.0')",
            default="",
        )
        extra_versions = versions_input.split() if versions_input else []
        setup_extra_versions(src_path, env_path, extra_versions)

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
