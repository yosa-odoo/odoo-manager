# Odoo workflow — aliases and functions
# Optional. Source manually from ~/.zshrc:
#   [ -f "<path-to-odoo-manager>/odoo.zsh" ] && source "<path-to-odoo-manager>/odoo.zsh"

# --- Environment ---

ce() {
    changexenv "$1"
    source "${ODOO_ENV_PATH}/Xenv/bin/activate"
}

oenv_activate() {
    source "${ODOO_ENV_PATH}/Xenv/bin/activate"
}

# --- Navigation ---

alias od="cd ..; cd odoo"
alias en="cd ..; cd enterprise"
alias o='source ~/odoo_tools/odoo-manager/_set_ovariables && cd "${ODOO_SRC_PATH}/$(getv)/odoo"'
alias e='source ~/odoo_tools/odoo-manager/_set_ovariables && cd "${ODOO_SRC_PATH}/$(getv)/enterprise"'

oshell() {
    local version=$(getv)
    local odoorc
    if [ -f "${ODOO_SRC_PATH}/$version/.odoorc" ]; then
        odoorc="${ODOO_SRC_PATH}/$version/.odoorc"
    else
        odoorc="$HOME/.odoorc"
    fi
    cd "${ODOO_SRC_PATH}/$version" && oenv_activate && ./odoo/odoo-bin shell -c "$odoorc" -d $(getdb)
}

# --- Database ---

alias getopw="getdb | cut -d '-' -f1"
alias getticket="getdb | cut -c1-7"
alias psqlo='psql -d $(getdb)'
alias apps='psql -d $(getdb) -c "SELECT name, state FROM ir_module_module WHERE state = '\''installed'\'';"'

# --- Help ---

odoo-help() {
    local highest=$(ls "$ODOO_ENV_PATH" | grep -E '^[0-9]{2}\.[0-9]$' | sort -V | tail -1)
    "$ODOO_SRC_PATH/$highest/odoo/odoo-bin" --help "$@"
}

# --- GitHub ---

alias gho='gh pr list --state all --base $(getv) --limit 20'

ghpr() {
    local TEMPLATE='{{- tablerow ("REPO" | color "blue+b") ("PR" | color "blue+b") ("CREATED" | color "blue+b") ("AUTHOR" | color "blue+b") ("TITLE" | color "blue+b") -}}
    {{- range . -}}
        {{- tablerow (.repository.nameWithOwner | color "yellow") (printf "#%v" .number | color "green+h") (timeago .createdAt | color "gray+h") (.author.login | color "cyan+h") .title -}}
    {{- end -}}'

    local GH_COMMAND="gh search prs --review-requested @me --state open --json repository,number,createdAt,title,author --template '$TEMPLATE'"

    FZF_DEFAULT_COMMAND="$GH_COMMAND" \
        GH_FORCE_TTY=100% fzf --ansi --disabled --no-multi --header-lines=1 \
        --header $'CTRL+B - Browser | CTRL+D - Diff | CTRL+X - Checkout\nCTRL+I - Info    | CTRL+Y - Comment' \
        --prompt 'Global PRs > ' --preview-window hidden:wrap \
        --layout=reverse --info=inline \
        --bind "change:reload:sleep 0.5; $GH_COMMAND {q} || true" \
        --bind 'ctrl-b:execute-silent(gh pr view {2} --repo {1} --web)' \
        --bind 'ctrl-d:toggle-preview+change-preview(gh pr diff {2} --repo {1} --color always)' \
        --bind 'ctrl-i:toggle-preview+change-preview(gh pr view {2} --repo {1})' \
        --bind 'ctrl-x:accept+execute(gh pr checkout {2} --repo {1})' \
        --bind 'ctrl-y:accept+execute(gh pr comment {2} --repo {1})'
}

# --- PyCharm ---

alias p="openpycharm"
alias pykill="killall java -9"
