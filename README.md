# Odoo (amazing) Tools

> **Note:** This tool only works with a **multi-version environment**. Each
> Odoo version must have its own source directory and its own Python virtual
> environment. For example:
>
> ```
> ~/src/          # one subdirectory per version
> ├── 16.0/
> ├── 17.0/
> └── ...
>
> ~/odoo-env/     # one virtualenv per version, matching the source directories
> ├── 16.0/
> ├── 17.0/
> └── ...
> ```
>
> One version = one Python environment. The tools rely on this structure to
> activate the correct virtualenv when switching between versions.

> **Note:** Some scripts referenced in this README (`b`, `new-odoo-version`,
> `sv`) are **not** part of this repository. They are user-defined companion
> scripts that this toolset integrates with. Their expected behaviour is
> described here for context.

### Install

Run the installer and follow the prompts:

```
python3 install.py
```

The installer first asks whether Odoo/enterprise are already cloned:

- **Fresh setup (no):** clones `odoo` and `enterprise` into `<src>/master/`,
  adds the `odoo-dev` remote to each, disables accidental pushes to `origin`,
  creates the `master` virtualenv, then optionally sets up additional versions
  (e.g. `17.0 18.0`) by calling `new-odoo-version`.
- **Existing setup (yes):** verifies that the source and virtualenv directories
  exist, offering to create any that are missing.

It then asks for the setup mode, the source and virtualenv paths, and the
shell config file to update. Two modes are available:

- `single`: one `~/.odoorc` shared across all versions
- `multi`: one `.odoorc` per version directory under the source path

The installer appends the scripts directory to `PATH` and sources the
bash completion file. Run with `--dry-run` to preview what would be
written without touching any file.

### Setup

To define and get the database you are working on, `setdb` and `getdb`
must be used.

- `setdb` takes one argument and writes the DB name into the `.odoorc`
  file for the current version (defaults to `odoo` if no argument given)
- `getdb` reads and returns the DB name from the same file
- `getv` prints the resolved Odoo version (useful for scripting)

All three rely on `_set_ovariables` (see [Version resolution](#version-resolution))
to locate the correct `.odoorc`.

### Switch

**`b` (external):**
Sets up the full Odoo environment for a given ticket or branch name. It
activates the right virtualenv, sets the DB name, and initializes the
DB if needed. This script is **not** part of this repository.

The basic usage is with a ticket number:

```
b 17.0-123456
b 17.0-123456 -i sale      # install a module after switching
b 17.0-123456 -I sale      # same, but drop and recreate the DB first
b 17.0-123456 -D           # install with demo data
```

The DB name is derived from the OPW number: `123456-17.0`. If no OPW
number is found in the name, the name itself is used as the DB name.

It can also be used with a branch name. In that case, the script looks
for a matching branch in the local repositories and checks it out:

```
b 17.0-some-branch
b 17.0-some-branch -f      # also search remote repositories
b 17.0-some-branch -R      # reset the local branch to the remote one
```

**`odoo-install`:**
Installs a list of modules on the current DB. Called by `b` but can
also be used directly.

```
odoo-install sale purchase       # install modules (drop and recreate DB first)
odoo-install -n sale             # install without dropping the DB
odoo-install -D sale             # install with demo data
```

The `-D` flag is version-aware: it passes `--with-demo` for Odoo 19.0
and above, and `--without-demo=False` for earlier versions.

After a fresh install, it automatically saves an `init` savepoint and
disables crons, and extends the database expiry date to avoid nag screens.

### Save & Restore

**`savepoint`:**
The core save/restore engine. `savedb` and `restoredb` are thin wrappers
around it.

```
savepoint [name]       # save current DB as <db>__<name> (default: SAVEPOINT)
savepoint -r [name]    # restore <db>__<name> into current DB
```

**`savedb`:**
Stores the state of the current DB and its filestore by copying it into a
new DB called `<current_db>__<savepoint name>`. The savepoint name defaults
to *SAVEPOINT* if not provided.

**`restoredb`:**
Restores the current DB from a savepoint. Takes one argument: the savepoint
name. Defaults to *SAVEPOINT*.

Both scripts determine the current DB via `getdb` and pass the resolved
version to avoid ambiguity.

### Flow example

I want to work on a DB called _1234567-15.0_:

```
b 1234567-15.0
```

I run Odoo, I create some products and set a specific configuration. I'm
going to follow some additional steps, but I want to create a backup
point first so that I can return to it later, and this state should be
called *config*:

```
savedb config
# This will copy the current DB to a new one called 1234567-15.0__config
```

I then go through several steps: I create a SO, confirm it, process the
delivery, create the invoice, etc. I'm about to post this invoice, but I
know that my bug appears right at that moment. In doubt, I first make
another backup, this time without worrying about the name:

```
savedb
# This will copy the current DB to a new one called 1234567-15.0__SAVEPOINT
```

I then post the invoice, try few things, change the code etc., and now I
would like to try again. I can simply restore my DB just before the
invoice posting:

```
restoredb
# This will copy the DB called 1234567-15.0__SAVEPOINT to the current one
```

Suppose now I would even like to change the configuration, but it's a
bit complicated because of the posted AML, some constraints, etc. I can
simply restore the first state I saved:

```
restoredb config
# This will copy the DB called 1234567-15.0__config to the current one
```

### Version management

These scripts manage the set of installed Odoo versions. They all accept
an explicit list of versions as arguments; if none is given, they derive
the list from the directories present in `~/odoo-env`.

**`new-odoo-version`:**
Sets up everything needed for a new Odoo version: git worktrees under
`<src>/<version>/`, a fresh virtualenv under `<env>/<version>/`,
and a `.odoorc` pre-filled with `db_name = <version>`. If the custom
`config-run` script is available, it is called to configure the IDE
project.

```
new-odoo-version 19.0
new-odoo-version saas-19.1 19.0   # set up several versions at once
```

**`update-version`:**
Pulls the latest changes for all versions in both the `odoo` and
`enterprise` repositories. Each version branch is rebased against its
remote counterpart; the currently checked-out branch is restored
afterwards. Sends a desktop notification via `notify-send` on completion
if available.

```
update-version              # update all versions found in <env>/
update-version 17.0 18.0   # update specific versions only
```

**`template-db`:**
Creates (or recreates) a template database for each version by running
`b <version> -I <modules>`. These templates are used by `b` to
initialise new DBs quickly without a full Odoo startup.

```
template-db              # rebuild templates for all versions
template-db 17.0 18.0   # rebuild for specific versions only
```

### Git utilities

**`rebase`:**
Rebases the current branch of a local `odoo` or `enterprise` repository
against its remote counterpart. Must be run from inside such a repository.

```
rebase           # rebase against origin/<version>
rebase -f        # fetch all remotes first, then rebase
```

### Dependency analysis

The `odoo-dependencies/` folder contains two Python scripts for exploring
module dependency graphs. Both auto-detect the current Odoo version from
the environment (via `OVERSION` or `~/.odoo_current_version`), or accept
an explicit `-o VERSION` flag.

**`search_dependencies.py`:**
Recursively lists all dependencies of a given module.

```
python3 odoo-dependencies/search_dependencies.py sale
python3 odoo-dependencies/search_dependencies.py sale -o 17.0
```

**`reverse_dependencies.py`:**
Recursively lists all modules that depend on a given module.

```
python3 odoo-dependencies/reverse_dependencies.py account
python3 odoo-dependencies/reverse_dependencies.py account -o 17.0
```

Both scripts scan the `odoo/addons`, `odoo/odoo/addons`, `enterprise`, and
`custom` directories under `~/src/<version>/`.

### Task cleanup

**`clean-task`:**
Removes everything associated with a task or ticket: local git branches in
both `odoo` and `enterprise` repositories, all matching databases, and their
filestores.

```
clean-task 1234567        # clean up by OPW number
clean-task some-branch    # clean up by branch name
```

### Version resolution

Most scripts source `_set_ovariables` to determine the active Odoo version
(`OVERSION`) and the path to the relevant `.odoorc` (`ORC_PATH`). The
resolution order is:

1. `-o <version>` option passed to the script
2. `GLOBAL_OVERSION` environment variable
3. Version extracted from the first argument (e.g. `17.0-123456`)
4. Output of the external `sv` script (name configurable via `SV_SCRIPT_NAME`)
5. `~/.odoo_current_version` — persisted from the last successful resolution
6. Fallback: `master`, or `FALLBACK_OVERSION` if set

`_set_ovariables` also sets two path variables used by all scripts:

- `ODOO_SRC_PATH` — base directory for Odoo source trees (default: `~/src`)
- `ODOO_ENV_PATH` — base directory for Python virtualenvs (default: `~/odoo-env`)

Both are written to `~/.odoo-manager.conf` by `install.py` and sourced by the
shell rc at startup. The fallbacks in `_set_ovariables` only apply when the
conf file is absent (e.g. before running the installer).

### Misc

This repository provides a few other scripts used internally by the above.

- `copydb` takes two arguments _X_ and _Y_, copies _X_ into a new DB
  called _Y_. Used internally by `savepoint` (and therefore `savedb`/`restoredb`)
- `killodoo` kills all running Odoo processes. Called by `copydb` since
  a live server prevents DB copies
- `ldb` lists all databases (`-a` also lists savepoints)
- `dropall` drops every database whose name contains the given string.
  Also accepts input from stdin (`ldb | grep foo | dropall`)
- `.bash_completion` enables tab-completion for `dropall`, `setdb`,
  `copydb`, `restoredb`, `savedb`, and `savepoint`
