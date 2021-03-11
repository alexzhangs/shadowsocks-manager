#? Common code, sourced by the other scripts.
#?

# exit on any error
set -e -o pipefail

if [[ -z $SSM_USER ]]; then
    declare SSM_USER=ssm
fi
declare INSTALL_DIR=/home/$SSM_USER/shadowsocks-manager
declare DJANGO_STATIC_DIR=/var/local/www/$SSM_USER/static/

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
        git clone https://github.com/alexzhangs/xsh
        bash xsh/install.sh
        . ~/.xshrc

        # load xsh libs
        xsh load xsh-lib/core
        xsh load xsh-lib/aws
    fi
}

check-os
