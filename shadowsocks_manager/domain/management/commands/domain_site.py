from django.core.management.base import BaseCommand
from django.conf import settings
from domain.models import Site

class Command(BaseCommand):
    help = 'Create or update the active django.contrib.sites.models.Site'
    django_default_options = ('verbosity', 'settings', 'pythonpath', 'traceback', 'no_color', 
                       'force_color', 'skip_checks')

    def add_arguments(self, parser):
        parser.add_argument('--name', type=str, nargs='?',
                            help='Site name. Required for creating a new site.'
                            'If this option is not set, the field will remain unchanged in update.'
                            'If this options is set with an empty value, the field will be'
                            'set or updated to blank.')
        parser.add_argument('--domain', type=str, nargs='?',
                            help='Site domain. Required for creating a new site.'
                            'If this option is not set, the field will remain unchanged in update.'
                            'If this options is set with an empty value, the field will be'
                            'set or updated to blank.')

    def handle(self, *args, **options):
        fields = self.get_fields(options)

        fields = {key: value for key, value in fields.items() if value is not None}

        site, created = Site.objects.update_or_create(pk=settings.SITE_ID, defaults=fields)
        self.stdout.write(self.style.SUCCESS('Successfully {0} site {1} with: {2}'.format('created' if created else 'updated', site.id, fields)))

    @classmethod
    def get_fields(cls, options):
        return {key: value for key, value in options.items() if key not in cls.django_default_options}