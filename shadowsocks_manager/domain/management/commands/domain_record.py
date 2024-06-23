from django.core.management.base import BaseCommand
from django.conf import settings
from domain.models import Record, Domain, Site

class Command(BaseCommand):
    help = 'Create or update domain.record'
    django_default_options = ('verbosity', 'settings', 'pythonpath', 'traceback', 'no_color', 
                       'force_color', 'skip_checks')

    def add_arguments(self, parser):
        parser.add_argument('--fqdn', type=str, nargs='?',
                            help='Fully Qualified Domain Name. '
                            'The host name and domain name (zone name) will be automatically resolved from this option. '
                            'If the domain name does not exist, the command will raise an error. '
                            'This option is ignored if both --host and --domain are used.')
        parser.add_argument('--host', type=str, nargs='?',
                            help='Host name without domain name. Example: `vpn`. '
                            'If --domain is used, this option is required.')
        parser.add_argument('--domain', type=str, nargs='?',
                            help='Root domain name or the delegated subdomain name. '
                            'Used as is, no resolution for the zone name. '
                            'If the domain name does not exist, the command will raise an error. '
                            'If --host is used, this option is required.')
        parser.add_argument('--type', type=str, nargs='?', default='A',
                            help='Record type. Default: `A`.')
        parser.add_argument('--answer', type=str, nargs='?',
                            help='Answer for the host name, comma "," is the delimiter for multiple answers.')
        parser.add_argument('--site', action='store_true',
                            help='Associate this record to the active django.contrib.sites.models.Site. '
                            'If the site does not exist, the command will raise an error.')

    def handle(self, *args, **options):
        fields = self.get_fields(options)
        fqdn = fields.get('fqdn')
        host = fields.get('host')
        domain = fields.get('domain')

        fields['site'] = Site.objects.get(pk=settings.SITE_ID) if fields['site'] else None

        if host and domain:
            fields['domain'] = Domain.objects.get(name=domain)
            record, created = Record.objects.update_or_create(host=host, domain=fields["domain"], defaults=fields)
        elif fqdn:
            fields.pop('host', None)
            fields.pop('domain', None)
            record, created = Record.objects.update_or_create(fqdn=fqdn, defaults=fields)
        else:
            self.print_help('manage.py', 'domain_record')
            return

        self.stdout.write(self.style.SUCCESS('Successfully {0} record: {1} {2} {3}, with site: {4}'.format(
            'created' if created else 'updated', record.type, record.host, record.domain.name,
            record.site.id if record.site else 'NULL')))

    @classmethod
    def get_fields(cls, options):
        return {key: value for key, value in options.items() if key not in cls.django_default_options}