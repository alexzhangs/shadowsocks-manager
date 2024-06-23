#!/usr/bin/env bash

#? Description:
#?   Setup shadowsocks-manager in your Python environment.
#?   If you need to run the setup under a specific Python environment, make
#?   sure to activate it before to run the setup.
#?
#? Usage:
#?   ssm-setup.sh [-e ENV ...]
#?                [-c] [-m] [-l] [-u USERNAME -p PASSWORD [-M EMAIL]] [-r PORT_BEGIN] [-R PORT_END]
#?                [-d DOMAIN [[-t TYPE] -a ANSWER]] [-E DNS_ENV [-n DNS_NAME]] [-S] [-h]
#?
#? Options:
#?   [-e ENV ...]
#?
#?   Set the environment variables in KEY=VALUE format for .ssm-env file.
#?   The .ssm-env file is used by Django settings.
#?   This option can be used multiple times.
#?
#?   The valid KEYs are:
#?
#?   - SSM_SECRET_KEY
#?
#?     Set Django's SECRET_KEY.
#?     The default value is hardcoded in the .ssm-env file and Django's settings.
#?     Do not use the default value in production environment.
#?     Below command will generate a random SECRET_KEY:
#?     ```sh
#?     $ od -vN 25 -An -tx1 /dev/urandom | tr -d ' \n'
#?     ```
#?
#?   - SSM_DEBUG
#?
#?     Set Django's DEBUG.
#?     The value can be 'True' or 'False'.
#?     The default value depends on the .ssm-env file and Django's settings.
#?     Do not use value SSM_DEBUG=True in production environment.
#?
#?   - SSM_TIME_ZONE
#?
#?     Set Django's TIME_ZONE.
#?     The value can be any valid timezone name.
#?     The default value depends on the .ssm-env file and Django's settings.
#?
#?   - SSM_ALLOWED_SITES_DEFAULTS
#?
#?     Set the default allowed sites for the shadowsocks-manager.
#?     The value can be any valid domain name and ip address, separated by comma.
#?     The default value depends on the .ssm-env file and Django's settings.
#?
#?   - SSM_ALLOWED_SITES_DEFAULTS_PLUS
#?
#?     Set the additional allowed sites for the shadowsocks-manager.
#?     The value can be any valid domain name and ip address, separated by comma.
#?     The default value depends on the .ssm-env file and Django's settings.
#?
#?   - SSM_ALLOWED_SITES_DYNAMIC_PUBLIC_IP
#?
#?     If set True, the server's public IP address is set for ALLOWED_HOSTS at runtime.
#?     The value can be 'True' or 'False'.
#?     The default value depends on the .ssm-env file and Django's settings.
#?
#?   - SSM_ALLOWED_SITES_NET_TIMEOUT
#?
#?     Set the timeout (in seconds) for the network request to get the server's public IP address.
#?     The default value depends on the .ssm-env file and Django's settings.
#?
#?   - SSM_ALLOWED_SITES_CACHE_TIMEOUT
#?
#?     Set the cache timeout (in seconds) for the site.domain and server's public IP address.
#?     The default value depends on the .ssm-env file and Django's settings.
#?
#?   - SSM_CACHES_BACKEND
#?
#?     Set the Django's cache backend.
#?     The value can be 'memcached.MemcachedCache'.
#?     The default value depends on the .ssm-env file and Django's settings.
#? 
#?   - SSM_MEMCACHED_HOST, SSM_MEMCACHED_PORT
#?
#?     Set the Memcached server's host and port which are used by Django cache.
#?     The default value depends on the .ssm-env file and Django's settings.
#?     These two KEYs are used only if SSM_CACHES_BACKEND is set to 'memcached.MemcachedCache'.
#? 
#?   - SSM_RABBITMQ_HOST, SSM_RABBITMQ_PORT
#?
#?     Set the RabbitMQ server's host and port which are used by Celery.
#?     The default value depends on the .ssm-env file and Django's settings.
#?
#?   However, this script will not check the validity of the KEYs and VALUEs.
#?
#?   [-c]
#?
#?   Collect Django static files.
#?   This is necessary for the first time setup.
#?
#?   [-m]
#?
#?   Migrate Django database.
#?   This is necessary for the first time setup.
#?
#?   [-l]
#?
#?   Load Django fixtures.
#?   This is necessary for the first time setup.
#?
#?   [-u USERNAME]
#?
#?   Username for shadowsocks-manager administrator.
#?   No default value.
#?   This is necessary for the first time setup.
#?
#?   [-p PASSWORD]
#?
#?   Password for shadowsocks-manager administrator'.
#?   No default value.
#?   This is necessary for the first time setup.
#?
#?   [-M EMAIL]
#?
#?   Email for the shadowsocks-manager administrator.
#?   Also, be used as the sender of the account notification Email.
#?   No default value.
#?
#?   [-r PORT_BEGIN]
#?
#?   The beginning port number for Shadowsocks nodes.
#?   The default value depends on the Django fixture data.
#?
#?   [-R PORT_END]
#?
#?   The ending port number for Shadowsocks nodes.
#?   The default value depends on the Django fixture data.
#?
#?   [-d DOMAIN]
#?
#?   The domain name (FQDN) for the shadowsocks-manager.
#?   No default value.
#?
#?   The zone name of the DOMAIN will be automatically resolved.
#?   Below table shows the example of the automatic resolution:
#?
#?   +-----------------------------+----+-------------------------+-----------------------+------------------------+
#?   | Domain to Resolve           | To | Resolved Zone Name      | Resolved by tools     | Resolved Reason        |
#?   +=============================+====+=========================+=======================+========================+
#?   | www.example.com             | => | example.com             | dnspython             | Root domain            |
#?   +-----------------------------+----+-------------------------+-----------------------+------------------------+
#?   | www.zone1.example.com       | => | zone1.example.com       | dnspython             | Delegated subdomain    |
#?   +-----------------------------+----+-------------------------+-----------------------+------------------------+
#?   | www.zone2.zone1.example.com | => | zone2.zone1.example.com | dnspython             | Delegated subdomain    |
#?   +-----------------------------+----+-------------------------+-----------------------+------------------------+
#?   | www.rootDomainNotExist.com  | => | rootDomainNotExist.com  | dnspython, TLDExtract | Fallback to TLDExtract |
#?   +-----------------------------+----+-------------------------+-----------------------+------------------------+
#?
#?   [-t TYPE]
#?
#?   The DNS record type for the domain name.
#?   The default value is `A`.
#?   This option is ignored if the DOMAIN or the ANSWER is not provided.
#?
#?   [-a ANSWER]
#?
#?   The DNS record answer for the domain name.
#?   No default value.
#?   This option is ignored if the DOMAIN is not provided.
#?
#?   [-n DNS_NAME]
#?
#?   The DNS_NAME names the NameServer for the DNS_ENV, and will be associated with the DOMAIN if provided.
#?   The default value is `nameserver`.
#?   This option is ignored if the DNS_ENV is not provided.
#?
#?   [-E DNS_ENV]
#?
#?   The DNS_ENV specifies the environment variables required to use the DNS API service.
#?   No default value.
#?
#?   Syntax: `PROVIDER={dns_provider},LEXICON_PROVIDER_NAME={dns_provider},LEXICON_{DNS_PROVIDER}_{OPTION}={value}[,...]`
#?
#?   The Python library `dns-lexicon` is leveraged to parse the DNS_ENV and access the DNS API.
#?   The required {OPTION} depends on the {dns_provider} that you use.
#?   For the list of supported {dns_provider} and {OPTION} please refer to:
#?   * https://dns-lexicon.readthedocs.io/en/latest/configuration_reference.html
#?
#?   [-S]
#?
#?   This option is ignored as it is processed by the docker-entrypoint.sh script.
#?
#?   [-h]
#?
#?   This help.
#?
#? Example:
#?   # First time setup in development environment:
#?   $ ssm-setup -c -m -l -u admin -p yourpassword
#?
#?   # Update a development environment to be production ready:
#?   $ ssm-setup -e SSM_SECRET_KEY=yourkey -e SSM_DEBUG=False
#?
#?   # First time setup in production environment:
#?   $ ssm-setup -e SSM_SECRET_KEY=yourkey -e SSM_DEBUG=False -c -m -l -u admin -p yourpassword -M admin@example.com
#?

# exit on any error
set -e -o pipefail

function usage () {
    awk '/^#\?/ {sub("^[ ]*#\\?[ ]?", ""); print}' "$0" \
        | awk '{gsub(/^[^ ]+.*/, "\033[1m&\033[0m"); print}'
}

function check-os () {
    if [[ $(uname) != 'Linux' && $(uname) != 'Darwin' ]]; then
        printf "fatal: this script support Linux and MacOS only.\n" >&2
        return 255
    fi
}

function main () {
    declare -a envs
    declare collect_flag=0 migrate_flag=0 loaddata_flag=0 \
            username password email port_begin port_end domain \
            type='A' answer dns_name='nameserver' dns_env \
            OPTIND OPTARG opt

    while getopts e:cmlu:p:M:r:R:d:t:a:n:E:Sh opt; do
        case $opt in
            e)
                envs+=("$OPTARG")
                ;;
            c)
                collect_flag=1
                ;;
            m)
                migrate_flag=1
                ;;
            l)
                loaddata_flag=1
                ;;
            u)
                username=$OPTARG
                ;;
            p)
                password=$OPTARG
                ;;
            M)
                email=$OPTARG
                ;;
            r)
                port_begin=$OPTARG
                ;;
            R)
                port_end=$OPTARG
                ;;
            d)
                domain=$OPTARG
                ;;
            t)
                type=$OPTARG
                ;;
            a) 
                answer=$OPTARG
                ;;
            n)
                dns_name=$OPTARG
                ;;
            E)
                dns_env=$OPTARG
                ;;
            S)
                # ignored
                ;;
            *)
                usage
                return 255
                ;;
        esac
    done

    if [[ $# -eq 0 ]]; then
        usage
        return 255
    fi

    check-os

    if [[ -n ${envs[*]} ]]; then
        ssm-dotenv -w "${envs[@]}"
    fi

    if [[ $collect_flag -eq 1 ]]; then
        ssm-manage collectstatic --no-input -c
    fi

    if [[ $migrate_flag -eq 1 ]]; then
        ssm-manage makemigrations
        ssm-manage migrate
    fi

    if [[ $loaddata_flag -eq 1 ]]; then
        ssm-manage loaddata auth.group.json \
               sites.site.json \
               django_celery_beat.crontabschedule.json \
               django_celery_beat.intervalschedule.json \
               django_celery_beat.periodictask.json \
               config.json \
               template.json
    fi

    if [[ -n $username && -n $password ]]; then
        ssm-manage superuser --username "$username" --password "$password" --email "$email"
    fi

    if [[ -n $port_begin ]]; then
        ssm-manage shadowsocks_config --port-begin "$port_begin"
    fi

    if [[ -n $port_end ]]; then
        ssm-manage shadowsocks_config --port-end "$port_end"
    fi

    if [[ -n $dns_env ]]; then
        ssm-manage domain_nameserver --name "$dns_name" --env "$dns_env"
    fi

    if [[ -n $domain ]]; then
        ssm-manage domain_domain --name "$domain" --nameserver "$dns_name"
        ssm-manage domain_site --domain "$domain"

        if [[ -n $type && -n $answer ]]; then
            ssm-manage domain_record --fqdn "$domain" --type "$type" --answer "$answer" --site
        fi
    fi
}

main "$@"

exit
