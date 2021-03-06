#? Common code, sourced by the other scripts.
#?

# exit on any error
set -e -o pipefail

declare SSM_USER=ssm
declare INSTALL_DIR=/home/$SSM_USER/shadowsocks-manager
declare DJANGO_STATIC_DIR=/var/local/www/$USER/static/

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
    # install xsh if missing
    if ! type xsh >/dev/null 2>&1; then
        git clone https://github.com/alexzhangs/xsh
        bash xsh/install.sh
    fi

    # load xsh libs
    xsh load xsh-lib/core
    xsh load xsh-lib/aws
}

check-os
