from django.core.management.base import BaseCommand
from domain.models import Site

class Command(BaseCommand):
    help = 'Create or update domain.models.Site'
    django_default_options = ('verbosity', 'settings', 'pythonpath', 'traceback', 'no_color', 
                       'force_color', 'skip_checks')

    def add_arguments(self, parser):
        parser.add_argument('--name', required=True,
                            help='Site name.')
        parser.add_argument('--domain', type=str, nargs='?',
                            help='Site domain. If this option is not set or set '
                            'with an empty value, the domain field will be set or '
                            'updated to blank.')

    def handle(self, *args, **options):
        fields = self.get_fields(options)

        # Site.domain accepts blank value but NULL value is not allowed
        if fields['domain'] is None:
            fields['domain'] = ''

        site, created = Site.objects.update_or_create(name=fields['name'], defaults=fields)
        self.stdout.write(self.style.SUCCESS('Successfully {0} site {1} with domain: {2}'.format('created' if created else 'updated', fields['name'], fields['domain'] or 'blank')))

    @classmethod
    def get_fields(cls, options):
        return {key: value for key, value in options.items() if key not in cls.django_default_options}