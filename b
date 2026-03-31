#!/bin/bash
# set -x

source _set_ovariables

function show_help {
  echo "Usage: b [OPTIONS] NAME"
  echo ""
  echo "Based on NAME, the script sets up the Odoo environment. It sets:"
  echo "- The OC/OE branch"
  echo "- The PY environment"
  echo "- The DB name"
  echo ""
  echo "Options:"
  echo "  -h, --help"
  echo "        Show help"
  echo "  -o VERSION, --odoo VERSION"
  echo "        Set Odoo version"
  echo "  -d DB, --database DB"
  echo "        Set database name"
  echo "  -f, --fetch"
  echo "        If NAME is considered as a branch and if that branch is not found "
  echo "        locally, try to find it on remote repositories"
  echo "  -R, --reset-branch"
  echo "        If the script finds the branch NAME, reset it with the remote one"
  echo "  -n, --no-init"
  echo "        Avoid DB initialization"
  echo "  -r, --restore"
  echo "        Force DB initialization (i.e., if the DB already exists, it will "
  echo "        restore it to its initialization savepoint"
  echo "  -i MODULES, --install-modules MODULES"
  echo "        Install the list of modules at the end of the configuration"
  echo "  -I MODULES, --init-modules MODULES"
  echo "        Same as -i but delete the existing DB first"
  echo "  -D, --with-demo"
  echo "        Install with demo data (passed to odoo-install)"
  echo ""
  echo "If NAME starts with '<version>-', the script will consider NAME as a potential"
  echo "branch name. It will therefore check in the local repositories to find and use"
  echo "it. Options -f and -R are only relevant in such situation."
  echo ""
  echo "If -d is not defined, the script will define the DB name itself:"
  echo "- If NAME is a branch and contains an OPW number, the DB name will be:"
  echo "  <opw number>-<version>[-fw]"
  echo "  (The part '-fw' is defined when the branch's author is fw-bot)"
  echo "- Else, NAME will be used as DB name"
  echo ""
  echo "If -o is not specified, the script will try to extract the odoo version from"
  echo "NAME. Without any identified version, the execution is interrupted."
  echo ""
  echo "Notes: "
  echo "  - If Odoo version is master, the DB initialization is automatically skipped."
}

killodoo

odoo=""
database=""
name=""
fetch=false
reset_branch=false
init=true
restore_init=false
modules_to_init=""
modules_to_install=""
with_demo=false


while [[ "$#" -gt 0 ]]; do
  case $1 in
    -h|--help)
      show_help
      exit 0
      ;;
    -o|--odoo)
      odoo="$2"
      shift
      ;;
    -d|--database)
      database="$2"
      shift
      ;;
    -f|--fetch)
      fetch=true
      ;;
    -R|--reset-branch)
      reset_branch=true
      ;;
    -n|--no-init)
      init=false
      ;;
    -r|--restore)
      restore_init=true
      ;;
    -i|--install-modules)
      modules_to_install="$2"
      shift
      ;;
    -I|--init-modules)
      modules_to_init="$2"
      shift
      ;;
    -D|--with-demo)
      with_demo=true
      ;;
    *)
      if [ -z "$name" ]
      then
        name="$1"
      else
        >&2 echo "Incorrect options/arguments"
        >&2 echo ""
        >&2 show_help
        exit 1
      fi
      ;;
  esac
  shift
done

explicit_name=$name
name=${name:-$(getdb)}

if [[ -z "$name" ]]; then
  >&2 echo "Missing fallback."
  exit 1
fi

if [[ "$name" =~ ^odoo-dev:.*|^enterprise-dev:.* ]]; then
  name=$(echo "$name" | cut -d ':' -f2)
fi
odoo=${odoo:-$name}
odoo=$(echo "$odoo" | grep -oE 'master|(saas-)?[0-9]{2}\.[0-9]' | head -1)

if [ -z "$odoo" ]
then
  >&2 echo "Missing version (or incorrect version format)."
  exit 1
fi



switch_branch() {
  repo="$1"
  branch_name="$2"
  fetch="$3"
  must_reset="$4"
  version="$5"
  cd "$ODOO_SRC_PATH"/"$version"/"$repo" || (>&2 echo "Repo $repo not found"; exit 1)

  branch=$(git branch | grep -E "$branch_name\$" >/dev/null && echo "$branch_name")
  if [ "$fetch" = true ] && [ -z "$branch" ]
  then
    echo "[$repo side] Nothing found. Looking on remote repo..."
    branch=$(git ls-remote --exit-code --heads dev "$branch_name" >/dev/null 2>&1 && git fetch dev "$branch_name" && echo "$branch_name")
  fi

  if [ "$branch" ]
  then
    git checkout -q "$branch"
    if [ "$must_reset" = true ]
    then
      echo "[$repo side] Resetting branch..."
      git fetch dev "$branch_name" >/dev/null 2>&1 && git reset --hard dev/"$branch_name" >/dev/null 2>&1 || echo "[$repo side] Reset failed."
    fi
    return 0
  fi
  return 1
}




if [ -n "$explicit_name" ] || [ -z "$modules_to_install" ]; then
  echo
  echo "Resetting to $odoo..."
  git -C "$ODOO_SRC_PATH/$odoo/odoo" checkout -q "$odoo" &
  git -C "$ODOO_SRC_PATH/$odoo/enterprise" checkout -q "$odoo" &
  wait
fi

if echo "$name" | grep -oEq '^master|(saas-)?[0-9]{2}\.[0-9]-.'
then
  echo
  echo "Looking for specific branch..."
  switch_branch odoo "$name" "$fetch" "$reset_branch" "$odoo" &
  oc_process=$!
  switch_branch enterprise "$name" "$fetch" "$reset_branch" "$odoo" &
  oe_process=$!

  wait $oc_process
  is_oc_branch=$?
  wait $oe_process
  is_oe_branch=$?

  if [ $is_oc_branch = 0 ] || [ $is_oe_branch = 0 ]
  then
    is_branch=true
  fi
fi



echo
echo "Specifying DB..."
if [ -z "$database" ]
then
  opw=$(echo "$name" | grep -oE '([0-9]{3,})' | head -1)
  if [ "$is_branch" = true ] && [ "$opw" ]
  then
    fw=$(echo "$name" | grep -Eo '\-fw$' || echo "")
    database=$opw-$odoo$fw
  else
    database=$name
  fi
fi
setdb "$database"


if [ -n "$modules_to_init" ]; then
  odoo-install $( [ "$with_demo" = true ] && echo "-D" ) "$modules_to_init"
elif [ "$odoo" != "master" ] && [ "$init" = true ] && ! ldb | grep -Eq "^$database$"
then
  template="${odoo}__init"
  if ldb -a | grep -Eq "^$template$"
  then
    echo
    echo "Initializing DB & Filestore..."
    createdb -T "$template" "$database"
    mkdir -p ~/.local/share/Odoo/filestore/"$database"
    cp -rf ~/.local/share/Odoo/filestore/"$odoo"/* ~/.local/share/Odoo/filestore/"$database"/
    savedb init
  fi
elif [ "$restore_init" = true ] && ldb -a | grep -Eq "^${database}__init$"
then
  echo
  echo "Restoring DB to initialization savepoint..."
  restoredb init
fi

if [ -n "$modules_to_install" ]; then
  odoo-install -n $( [ "$with_demo" = true ] && echo "-D" ) "$modules_to_install"
fi

