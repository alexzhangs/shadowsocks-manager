from django.core.management.base import BaseCommand
from domain.models import NameServer

class Command(BaseCommand):
    help = 'Create or update domain.models.NameServer'
    django_default_options = ('verbosity', 'settings', 'pythonpath', 'traceback', 'no_color', 
                       'force_color', 'skip_checks')

    def add_arguments(self, parser):
        parser.add_argument('--name', required=True,
                            help='NameServer name. If a nameserver with the same name exists, '
                            'the command will update the nameserver.')
        parser.add_argument('--env', type=str, nargs='?')

    def handle(self, *args, **options):
        fields = self.get_fields(options)
        _, created = NameServer.objects.update_or_create(name=fields["name"], defaults=fields)
        self.stdout.write(self.style.SUCCESS('Successfully {0} nameserver: {1}'.format('created' if created else 'updated', fields["name"])))

    @classmethod
    def get_fields(cls, options):
        return {key: value for key, value in options.items() if key not in cls.django_default_options}