from django.core.management.base import BaseCommand
from shadowsocksz.models import Config

class Command(BaseCommand):
    help = 'Set shadowsocksz config parameters'
    django_default_options = ('verbosity', 'settings', 'pythonpath', 'traceback', 'no_color', 
                       'force_color', 'skip_checks')

    def add_arguments(self, parser):
        parser.add_argument('--port-begin', type=int, nargs='?')
        parser.add_argument('--port-end', type=int, nargs='?')
        parser.add_argument('--timeout-remote', type=float, nargs='?')
        parser.add_argument('--timeout-local', type=float, nargs='?')
        parser.add_argument('--cache-timeout', type=float, nargs='?')

    def handle(self, *args, **options):
        for key, value in options.items():
            if key in self.django_default_options:
                # skip django default options
                continue

            if value is not None:
                Config.objects.update(**{key: value})
                self.stdout.write(self.style.SUCCESS(f'Successfully set shadowsocksz.config.{key} to {value}'))
