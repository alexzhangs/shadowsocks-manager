from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
 
class Command(BaseCommand):
    help = 'Create superuser with the given username, password and email.'
    django_default_options = ('verbosity', 'settings', 'pythonpath', 'traceback', 'no_color', 
                       'force_color', 'skip_checks')

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)
        parser.add_argument('--password', required=True)
        parser.add_argument('--email', type=str, nargs='?')

    def handle(self, *args, **options):
        fields = self.get_fields(options)
        username = fields.get('username')
        password = fields.get('password')
        email = fields.get('email')

        User.objects.filter(username=username).delete()
        User.objects.create_superuser(username, email, password)
        self.stdout.write(self.style.SUCCESS('Successfully created superuser: {0}'.format(username)))

    @classmethod
    def get_fields(cls, options):
        return {key: value for key, value in options.items() if key not in cls.django_default_options}