#!/usr/bin/env bash

#? Description:
#?   This script is the entrypoint for the shadowsocks-manager container.
#?   It will:
#?   - Call the docker-ssm-setup.sh
#?   - Setup the Nginx to use HTTPS (if the HTTPS mode is enabled)
#?   - Issue the TLS certificate with acme.sh (if the HTTPS mode is enabled)
#?   - Start the uWSGI and celery services
#?   - Start the nginx service
#?
#?   This script should be called by user root.
#?
#? Usage:
#?   docker-entrypoint.sh [-d DOMAIN] [-E DNS_ENV] [-S] [SSM_SETUP_OPTIONS]
#?   docker-entrypoint.sh [-h]
#?
#? Options:
#?   [-d DOMAIN]
#?
#?   The domain name (FQDN) for the shadowsocks-manager.
#?   No default value.
#?
#?   This option is used as the Nginx server name and will be also passed down to docker-ssm-setup.sh.
#?
#?   [-E DNS_ENV]
#?
#?   The DNS_ENV specifies the environment variables required to use the DNS API service.
#?   No default value.
#?
#?   This option is used to automate TLS certificate issuance and will be also passed down to docker-ssm-setup.sh.
#?
#?   Syntax: `PROVIDER={dns_provider},LEXICON_PROVIDER_NAME={dns_provider},LEXICON_{DNS_PROVIDER}_{OPTION}={value}[,...]`
#?
#?   The Python library `dns-lexicon` is leveraged to parse the DNS_ENV and access the DNS API.
#?   The required {OPTION} depends on the {dns_provider} that you use.
#?   For the list of supported {dns_provider} and {OPTION} please refer to:
#?   * https://dns-lexicon.readthedocs.io/en/latest/configuration_reference.html
#?  
#?   Speciallly, an extra environment variable `PROVIDER` is used to repeat the {dns_provider} for
#?   the convenience of using the DNS_ENV in `acme.sh` with the `--dns dns_lexicon` option.
#?   * https://github.com/acmesh-official/acme.sh/wiki/dnsapi
#?   * https://github.com/acmesh-official/acme.sh/wiki/How-to-use-lexicon-DNS-API
#?  
#?   Sample: `PROVIDER=namecom,LEXICON_PROVIDER_NAME=namecom,LEXICON_NAMECOM_AUTH_USERNAME=your_username,LEXICON_NAMECOM_AUTH_TOKEN=your_token`
#?  
#?   This option is essential to automate the DNS record management. They are used
#?   in several places depending on you configuration:
#?  
#?   +-------------------------+----------------------------+-------------------------+---------------------------+----------------------+-----------------+------------------+
#?   | Project                 | Component                  | DNS Library             | Usage                     | Purpose              | Impacted Domain | Impacted Feature |
#?   +=========================+============================+=========================+===========================+======================+=================+==================+
#?   | shadowsocks-manager     | docker-entrypoint.sh       | acme.sh => dns-lexicon  | domain owner verification | issuing certificates | SSM_DOMAIN      | Nginx HTTPS      |
#?   +-------------------------+----------------------------+-------------------------+---------------------------+----------------------+-----------------+------------------+
#?   | shadowsocks-manager     | domain/models.py           | dns-lexicon             | DNS record management     | DNS record sync      | SSM_DOMAIN      | DNS record sync  |
#?   |                         |                            |                         |                           |                      | SS_DOMAIN       |                  |
#?   |                         |                            |                         |                           |                      | L2TP_DOMAIN     |                  |
#?   +-------------------------+----------------------------+-------------------------+---------------------------+----------------------+-----------------+------------------+
#?  
#?   If goes without env `DNS_ENV`, the manual step will be required for the domain owner verification.
#?
#?   [-S]
#?
#?   Use -S to enable the HTTPS mode on Nginx.
#?   If the HTTPS mode is enabled, the HTTP traffic will be redirected to HTTPS.
#?
#?   [SSM_SETUP_OPTIONS]
#?
#?   Options are the same as the docker-ssm-setup script.
#?   If any option is provided, the options will pass to the docker-ssm-setup script.
#?
#?   [-h]
#?
#?   This help.
#?
#? Environment:
#?   The following environment variables are used by this script and being set by the Dockerfile:
#?
#?   - SSM_USER
#?
#?     Required.
#?     Set the non-root user to run the ssm-setup.sh script.
#?     The user should exist in the container.
#?
#?   - SSM_DATA_HOME
#?
#?     Required.
#?     Set the data home directory for shadowsocks-manager in the container.
#?     The path should exist in the container and should be writable by the SSM_USER.
#?     It should be mounted as a volume in the container while running the docker image.
#?
#?   - SSM_ENV
#?
#?     Required.
#?     Expose environment variables to superivsord.
#?
#? File:
#?   The following files conditionally created by this script:
#?
#?   - ~/.nginx-setup-done-{DOMAIN}
#?
#?     This file is created after the Nginx setup for the domain with HTTPS.
#?     The Nginx setup will be skipped if this file exists.
#?
#?   - ~/.acme-account-done-{DOMAIN}
#?
#?     This file is created after the account registration with acme.sh.
#?     The account registration will be skipped if this file exists.
#?
#?   - ~/.acme-cert-done-{DOMAIN}
#?
#?     This file is created after the certificate is issued for the domain with acme.sh.
#?     The certificate issuance will be skipped if this file exists.
#?
#? Example:
#?   # for the development environment
#?   $ docker-entrypoint.sh
#?
#?   # for the production environment
#?   $ docker-entrypoint.sh -e SSM_SECRET_KEY=yourkey -e SSM_DEBUG=False -u admin -p yourpassword -M admin@yourdomain.com
#?
#?   # using domain name without enabling DNS API and HTTPS
#?   $ docker-entrypoint.sh -d admin.ss.dev.yourdomain.com
#?
#?   # using domain name with enabling DNS API but not HTTPS
#?   $ docker-entrypoint.sh -d admin.ss.dev.yourdomain.com \
#?       -E PROVIDER=namecom,LEXICON_PROVIDER_NAME=namecom,LEXICON_NAMECOM_AUTH_USERNAME=$Namecom_Username,LEXICON_NAMECOM_AUTH_TOKEN=$Namecom_Token
#?
#?   # using domain name with enabling both DNS API and HTTPS
#?   $ docker-entrypoint.sh -d admin.ss.dev.yourdomain.com -S \
#?       -E SSM_DNS_ENV=PROVIDER=namecom,LEXICON_PROVIDER_NAME=namecom,LEXICON_NAMECOM_AUTH_USERNAME=$Namecom_Username,LEXICON_NAMECOM_AUTH_TOKEN=$Namecom_Token \
#?

# exit on any error
set -e -o pipefail

function usage () {
    awk '/^#\?/ {sub("^[ ]*#\\?[ ]?", ""); print}' "$0" \
        | awk '{gsub(/^[^ ]+.*/, "\033[1m&\033[0m"); print}'
}

function nginx-setup () {
    #? Description:
    #?   Setup the Nginx to use HTTPS.
    #?
    #? Usage:
    #?   nginx-setup DOMAIN
    #?

    declare domain=${1:?}

    declare nginx_setup_done_file=~/.nginx-setup-done-${domain}

    if [[ -f $nginx_setup_done_file ]]; then
        echo "INFO: Nginx had been setup for the domain $domain before."
        return
    fi

    # Link the SSL certificate and key to the Nginx directory
    (cd /etc/nginx/ssl \
        && ln -sf "/root/.acme.sh/${domain}/fullchain.cer" ssm.cer \
        && ln -sf "/root/.acme.sh/${domain}/${domain}.key" ssm.key
    )

    # Link the HTTPS configuration to the Nginx directory
    (cd /etc/nginx/sites-available \
        && ln -sf ssm-https.conf ssm.conf
    )

    # Create the HTTPS setup done file
    touch "$nginx_setup_done_file"
}

function issue-tls-cert () {
    #? Description:
    #?   Issue a TLS certificate with acme.sh.
    #?
    #? Usage:
    #?   issue-tls-cert DOMAIN DNS DNS_ENV [--renew-hook "COMMAND"]
    #?

    declare domain=${1:?} dns=$2 dns_env=$3 renew_opts=("${@:4}")

    declare acme_account_done_file=~/.acme-account-done-${domain}
    declare acme_cert_done_file=~/.acme-cert-done-${domain}

    if [[ -f $acme_cert_done_file ]]; then
        echo "INFO: TLS certificate had been issued for the domain $domain before."
        return
    fi

    acme.sh --version

    # Register an account with acme.sh if not done
    if [[ ! -f $acme_account_done_file ]]; then
        acme.sh --register-account -m "acme@$domain"
        touch "$acme_account_done_file"
    fi

    declare -a acme_common_opts=(--force-color --domain "$domain")
    declare -a acme_issue_opts=("${acme_common_opts[@]}" "${renew_opts[@]}" --dns)

    # Setup DNS hook if DNS_ENV is set
    if [[ -n $dns ]]; then
        # Check if the dns_env is set
        if [[ -z $dns_env ]]; then
            echo "WARNING: dns_env is not set." >&2
        fi

        declare -a dns_envs
        # Read the DNS_ENV into an array
        IFS=',' read -r -a dns_envs <<< "$dns_env"

        # Export the dns_envs
        export "${dns_envs[@]}"

        # Issue a certificate for the domain with acme.sh, using DNS hook
        acme.sh --issue "${acme_issue_opts[@]}" "$dns"
    else
        # Issue a certificate for the domain with acme.sh, using manual mode, ignoring the non-zero exit code
        acme.sh --issue "${acme_issue_opts[@]}" --yes-I-know-dns-manual-mode-enough-go-ahead-please || :

        while true; do
            echo "Sleeping for 60 seconds to allow the DNS record to propagate ..."
            sleep 60

            # Verify the domain owner
            if acme.sh --renew "${acme_common_opts[@]}" --yes-I-know-dns-manual-mode-enough-go-ahead-please; then
                break
            fi
        done
    fi

    # Create a symbolic link for the certificate directory, v2ray-plugin seaches only the path without the _ecc suffix
    ln -s "${domain}_ecc" "/root/.acme.sh/${domain}"

    # Create the cert done file
    touch "$acme_cert_done_file"
}

function main () {
    declare domain dns_env https_flag=0 \
            OPTIND OPTARG opt

    while getopts d:E:Sh opt; do
        case $opt in
            d)
                domain=$OPTARG
                ;;
            E)
                dns_env=$OPTARG
                ;;
            S)
                https_flag=1
                ;;
            h)
                usage
                return
                ;;
            *)
                # ignored as they are processed by the docker-ssm-setup.sh
                ;;
        esac
    done

    if [[ $# -eq 0 ]]; then
        usage
        return 255
    fi

    # Check if the SSM_USER and SSM_DATA_HOME are set

    if [[ -z $SSM_USER ]]; then
        echo "SSM_USER is not set."
        return 255
    fi

    if [[ -z $SSM_DATA_HOME ]]; then
        echo "SSM_DATA_HOME is not set."
        return 255
    fi

    # Check if the SSM_USER and SSM_DATA_HOME are valid

    if ! id -u "$SSM_USER" &>/dev/null; then
        echo "$SSM_USER: The user SSM_USER does not exist."
        return 255
    fi

    if [[ ! -e $SSM_DATA_HOME ]]; then
        echo "$SSM_DATA_HOME: The path SSM_DATA_HOME does not exist."
        return 255
    fi

    # Set the owner of the SSM_DATA_HOME to the SSM_USER
    chown -R "$SSM_USER:$SSM_USER" "$SSM_DATA_HOME"

    # Call docker-ssm-setup.sh under the SSM_USER
    sudo -u "$SSM_USER" --preserve-env=SSM_DATA_HOME "$(cd "$(dirname "$0")" && pwd)"/docker-ssm-setup.sh "$@"

    if [[ $https_flag -eq 1 ]]; then
        # Setup the nginx to use HTTPS
        nginx-setup "$domain"

        # Issue a TLS certificate
        issue-tls-cert "$domain" "dns_lexicon" "$dns_env" --renew-hook 'nginx -s reload'
    fi

    # Set the possible supervisor configuration files
    declare supervisor_confs=(
        /etc/supervisor/supervisord.conf  # Debian
        /etc/supervisord.conf  # Alpine
    )
    # Start the uWSGI and celery services
    declare supervisor_conf
    for supervisor_conf in "${supervisor_confs[@]}"; do
        if [[ -f $supervisor_conf ]]; then
            echo "Starting supervisord ..."
            supervisord -c "$supervisor_conf"
            break
        fi
    done

    # Start the nginx in the foreground
    echo "Starting nginx ..."
    nginx -g "daemon off;"
}

main "$@"

exit
