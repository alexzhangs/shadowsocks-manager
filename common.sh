#? Common code, sourced by the other scripts.
#?

# exit on any error
set -e -o pipefail

function usage () {
    awk '/^#\?/ {sub("^[ ]*#\\?[ ]?", ""); print}' "$0" \
        | awk '{gsub(/^[^ ]+.*/, "\033[1m&\033[0m"); print}'
}

function check-os () {
    if [[ $(uname) != 'Linux' ]]; then
        printf "error: this script support Linux only.\n" >&2
        return 255
    fi
}

function install-xsh () {
    if [[ -f ~/.xshrc ]]; then
        . ~/.xshrc
    fi
    # install xsh if missing
    if ! type xsh >/dev/null 2>&1; then
        curl -s https://raw.githubusercontent.com/alexzhangs/xsh/master/boot | bash && . ~/.xshrc

        # load xsh libs
        xsh load xsh-lib/core
        xsh load xsh-lib/aws
    fi
}

check-os
install-xsh

if [[ -z $SSM_USER ]]; then
    declare SSM_USER=ssm
fi

declare VENV_HOME=$(xsh /os/user/home "$SSM_USER")
declare VENV_DIR=$VENV_HOME/$SSM_USER
declare INSTALL_DIR=/home/$SSM_USER/shadowsocks-manager
declare DJANGO_STATIC_DIR=/var/local/www/$SSM_USER/static/

