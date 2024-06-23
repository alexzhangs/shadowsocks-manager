from django.core.management.base import BaseCommand
from domain.models import Domain, NameServer

class Command(BaseCommand):
    help = 'Create or update domain.models.Domain'
    django_default_options = ('verbosity', 'settings', 'pythonpath', 'traceback', 'no_color', 
                       'force_color', 'skip_checks')

    def add_arguments(self, parser):
        parser.add_argument('--name', required=True,
                            help='Domain name. '
                            'If the domain name is not root domain name, '
                            'the zone name will be resolved automatically. '
                            'If a domain with the same name exists, '
                            'the command will update the domain.')
        parser.add_argument('--nameserver', type=str, nargs='?',
                            help='NameServer name. If this option is not set or set '
                            'with an empty value, the nameserver field will be set or '
                            'updated to NULL. If the nameserver does not exist, the '
                            'command will raise an error.')

    def handle(self, *args, **options):
        fields = self.get_fields(options)

        fields['nameserver'] = NameServer.objects.get(name=fields['nameserver']) if fields['nameserver'] else None

        domain, created = Domain.objects.update_or_create(name=fields['name'], defaults=fields)
        self.stdout.write(self.style.SUCCESS('Successfully {0} domain {1} from the input: {2}'.format('created' if created else 'updated', domain.name, fields['name'])))

    @classmethod
    def get_fields(cls, options):
        return {key: value for key, value in options.items() if key not in cls.django_default_options}