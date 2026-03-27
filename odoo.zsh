# WARNING NOT CLEANED UP YET 

# Odoo workflow — aliases and functions
# Sourced from ~/.zshrc via the odoo-manager block at the bottom

# --- Environment ---

ce() {
    changexenv "$1"
    source "$HOME/odoo-env/Xenv/bin/activate"
}

oenv_activate() {
    source ~/odoo-env/Xenv/bin/activate
}

# --- Navigation ---

alias od="cd ..; cd odoo"
alias en="cd ..; cd enterprise"
alias o="cd ~/src/\$(getv)/odoo"
alias e="cd ~/src/\$(getv)/enterprise"
alias oshell="o && oenv_activate && cd .. && ./odoo/odoo-bin shell -d \$(getdb)"

# --- Database ---

alias getopw="getdb | cut -d '-' -f1"
alias psqlo="psql -d \$(getdb)"
alias apps="psql -d \$(getdb) -c \"SELECT name, state FROM ir_module_module WHERE state = 'installed';\""

# --- Tools ---

alias bb="b \$(sb)"
alias com="copy_odoo_module"
alias sdv="setdbversion"
alias mailhog="~/go/bin/MailHog"
alias applytemp="ls ~/temp/ | fzf -e | git apply"
alias search_depends="python3 ~/odoo_tools/odoo-manager/odoo-dependencies/search_dependencies.py"
alias reverse_depends="python3 ~/odoo_tools/odoo-manager/odoo-dependencies/reverse_dependencies.py"
alias dd="python3 ~/odoo_tools/difference_days.py"
alias whosoff="~/odoo-env/16.0/bin/python3 ~/odoo_tools/who_is_off.py"
alias tickets="~/odoo_tools/env_odoo_tools/bin/python3 ~/odoo_tools/pta/tickets.py | xclip -selection clipboard"
alias dtickets="~/odoo_tools/env_odoo_tools/bin/python3 ~/odoo_tools/tickets.py --dispatch | xclip -selection clipboard"
alias oe-support="/home/odoo/Documents/config/odoo/oe-support.sh"
alias done_ticket="/home/odoo/Documents/config/odoo/done_ticket.sh"
alias oc="odoorc-oc"
alias oe="odoorc-oe"

# odoo-help: use the highest installed version (excluding master)
_odoo_highest=$(ls "$HOME/odoo-env" | grep -E '^[0-9]{2}\.[0-9]$' | sort -V | tail -1)
alias odoo-help="$HOME/src/$_odoo_highest/odoo/odoo-bin --help"
unset _odoo_highest

# --- GitHub ---

alias gho="gh pr list --state all --base \$(getv) --limit 20"

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
