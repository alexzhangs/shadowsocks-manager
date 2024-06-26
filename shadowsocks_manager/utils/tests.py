# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals

import os
import random
import string
import shutil
import subprocess
from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth.models import User
import tempfile
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

from utils.viewsets import CompatModelViewSet
from utils.version import __version__, __build__, set_buildno, get_buildno, get_version

import logging
# Get a logger for this django app
logger = logging.getLogger(__name__.split('.')[-2])
# Set the logging level to make the output clean
logger.setLevel(logging.CRITICAL)


class CompatModelViewSetTestCase(TestCase):
    def test_compatmodelviewset_py2(self):
        class Py2ViewSet(CompatModelViewSet):
            filter_fields = ['foo']

        obj = Py2ViewSet()
        self.assertTrue(any(getattr(obj, attr, None) == ['foo'] for attr in ['filter_fields', 'filterset_fields']))

    def test_compatmodelviewset_py3(self):
        class Py3ViewSet(CompatModelViewSet):
            filterset_fields = ['foo']

        obj = Py3ViewSet()
        self.assertTrue(any(getattr(obj, attr, None) == ['foo'] for attr in ['filter_fields', 'filterset_fields']))


class VersionTestCase(TestCase):
    def test_version_set_buildno(self):
        with tempfile.NamedTemporaryFile(mode='w+', delete=True) as f:
            initial_content = '__build__ = ""\n'
            f.write(initial_content)
            f.flush() 

            set_buildno('abcdef0', f.name)

            f.seek(0)
            self.assertIn('abcdef0', f.read())

    def test_version_get_buildno(self):
        self.assertTrue(get_buildno())

    @patch('subprocess.check_output')
    def test_version_get_buildno_missing_git_dir(self, mock_check_output):
        def custom_check_output_side_effect(*args, **kwargs):
            if args[0] == ['/usr/bin/git', 'rev-parse', '--is-inside-work-tree']:
                return b''

        mock_check_output.side_effect = custom_check_output_side_effect
        result = get_buildno()
        self.assertEqual(result, '')

    @patch('subprocess.check_output')
    def test_version_get_buildno_clean(self, mock_check_output):
        def custom_check_output_side_effect(*args, **kwargs):
            if args[0] == ['/usr/bin/git', 'rev-parse', '--is-inside-work-tree']:
                return b'true\n'
            elif args[0] == ['/usr/bin/git', 'rev-parse', '--short', 'HEAD']:
                return b'abcdef0\n'
            elif args[0] == ['/usr/bin/git', 'status', '--porcelain']:
                return b''

        mock_check_output.side_effect = custom_check_output_side_effect
        self.assertRegex(get_buildno(), r'^[a-f0-9]+$')

    @patch('subprocess.check_output')
    def test_version_get_buildno_dirty(self, mock_check_output):
        def custom_check_output_side_effect(*args, **kwargs):
            if args[0] == ['/usr/bin/git', 'rev-parse', '--is-inside-work-tree']:
                return b'true\n'
            elif args[0] == ['/usr/bin/git', 'rev-parse', '--short', 'HEAD']:
                return b'abcdef0\n'
            elif args[0] == ['/usr/bin/git', 'status', '--porcelain']:
                return b'M dirty_file\n'

        mock_check_output.side_effect = custom_check_output_side_effect
        self.assertRegex(get_buildno(), r'^[a-f0-9]+-\d{8}-\d{4}$')

    def test_version_get_version(self):
        self.assertEqual(get_version(), 'v{}'.format(__version__))

    def test_version_get_version_full(self):
        self.assertEqual(get_version(full=True), 'v{}-{}'.format(__version__, __build__ or get_buildno()))

    custom_build = 'abcdef0-20201231-2359'
    @patch('utils.version.__build__', custom_build)
    def test_version_get_version_full_with_custom_build(self):
        self.assertEqual(get_version(full=True), 'v{}-{}'.format(__version__, self.custom_build))

    @patch('utils.version.get_buildno')
    def test_version_get_version_full_with_no_build(self, mock_get_buildno):
        mock_get_buildno.return_value = ''
        self.assertEqual(get_version(full=True), 'v{}'.format(__version__))


class ManagementCommandsTestCase(TestCase):
    password = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(12))

    def test_cmd_superuser(self):
        call_command('superuser', '--username', 'testadmin', '--password', self.password)
        self.assertTrue(User.objects.filter(username='testadmin').exists())

        call_command('superuser', '--username', 'testadmin', '--password', self.password, '--email', 'testadmin@example.com')
        self.assertTrue(User.objects.filter(username='testadmin', email='testadmin@example.com').exists())

    def test_cli_superuser(self):
        # this user may be created in the regular db rather than the test db
        result = subprocess.Popen(['ssm-manage', 'superuser', '--username', 'testadmin', '--password', self.password],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        self.assertEqual(result.returncode, 0)
        self.assertIn('Successfully created superuser', output.strip('\n'))

class ScriptTestCase(TestCase):
    # Get the coverage file name from the environment variable, set by tox
    coverage_file = os.environ.get('COVERAGE_FILE')
    os.environ['COVERAGE_FILE'] = '{}.utils.script'.format(coverage_file)

    def setUp(self):
        # Set default runner
        self.script_runner = ['python']

        if self.coverage_file:
            self.script_runner = ['coverage', 'run']

        self.ssm_data_home = os.environ.get('SSM_DATA_HOME') or os.path.expanduser('~/.ssm-data')
        self.ssm_env_file = os.path.join(self.ssm_data_home, '.ssm-env')
        if os.path.exists(self.ssm_env_file):
            # backup the .ssm-env file
            shutil.copy(self.ssm_env_file, '{}.bak'.format(self.ssm_env_file))

    def tearDown(self):
        # restore the .ssm-env file
        if os.path.exists('{}.bak'.format(self.ssm_env_file)):
            os.rename('{}.bak'.format(self.ssm_env_file), self.ssm_env_file)

    def test_script_main(self):
        result = subprocess.Popen(self.script_runner + ['shadowsocks_manager/__main__.py', 'ls', '-1', '__main__.py'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        self.assertFalse(error)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(output.strip('\n'), '__main__.py')

    def test_cli_main(self):
        result = subprocess.Popen(['ssm', 'ls', '-1', '__main__.py'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        self.assertFalse(error)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(output.strip('\n'), '__main__.py')

    def test_script_manage(self):
        result = subprocess.Popen(self.script_runner + ['shadowsocks_manager/utils/manage.py', 'check'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        self.assertFalse(error)
        self.assertEqual(result.returncode, 0)
        self.assertIn('no issues', output.strip('\n'))

    def test_cli_manage(self):
        result = subprocess.Popen(['ssm-manage', 'check'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        self.assertFalse(error)
        self.assertEqual(result.returncode, 0)
        self.assertIn('no issues', output.strip('\n'))

    def test_script_dotenv(self):
        result = subprocess.Popen(self.script_runner + ['shadowsocks_manager/utils/dotenv.py', '-w', 'TEST=1'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        self.assertFalse(error)
        self.assertEqual(result.returncode, 0)

        result = subprocess.Popen(self.script_runner + ['shadowsocks_manager/utils/dotenv.py'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        self.assertFalse(error)
        self.assertEqual(result.returncode, 0)
        self.assertIn('TEST=1', output.strip('\n'))

        result = subprocess.Popen(self.script_runner + ['shadowsocks_manager/utils/dotenv.py', '-w', 'TEST=2'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        self.assertFalse(error)
        self.assertEqual(result.returncode, 0)

        result = subprocess.Popen(self.script_runner + ['shadowsocks_manager/utils/dotenv.py'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        self.assertFalse(error)
        self.assertEqual(result.returncode, 0)
        self.assertIn('TEST=2', output.strip('\n'))

    def test_cli_dotenv(self):
        result = subprocess.Popen(['ssm-dotenv', '-w', 'TEST=1'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        self.assertFalse(error)
        self.assertEqual(result.returncode, 0)

    def test_script_celery(self):
        result = subprocess.Popen(self.script_runner + ['shadowsocks_manager/utils/celery_app.py', '--version'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        self.assertFalse(error)
        self.assertEqual(result.returncode, 0)
        self.assertRegex(output.strip('\n'), r'\d+\.\d+\.\d+')

    def test_cli_celery(self):
        result = subprocess.Popen(['ssm-celery', '--version'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        self.assertFalse(error)
        self.assertEqual(result.returncode, 0)
        self.assertRegex(output.strip('\n'), r'\d+\.\d+\.\d+')

    def test_script_uwsgi(self):
        result = subprocess.Popen(self.script_runner + ['shadowsocks_manager/utils/uwsgi.py', '--version'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        #self.assertFalse(error)
        self.assertEqual(result.returncode, 0)
        self.assertRegex(output.strip('\n'), r'\d+\.\d+\.\d+')

    def test_cli_uwsgi(self):
        result = subprocess.Popen(['ssm-uwsgi', '--version'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        #self.assertFalse(error)
        self.assertEqual(result.returncode, 0)
        self.assertRegex(output.strip('\n'), r'\d+\.\d+\.\d+')

    def test_script_version(self):
        result = subprocess.Popen(self.script_runner + ['shadowsocks_manager/utils/version.py'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        self.assertFalse(error)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(output.strip('\n'), 'v{}'.format(__version__))

    def test_script_version_full(self):
        result = subprocess.Popen(self.script_runner + ['shadowsocks_manager/utils/version.py', '--full'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        self.assertFalse(error)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(output.strip('\n'), 'v{}-{}'.format(__version__, __build__ or get_buildno()))

    def test_script_version_get_build(self):
        result = subprocess.Popen(self.script_runner + ['shadowsocks_manager/utils/version.py', '--get-build'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        self.assertFalse(error)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(output.strip('\n'), get_buildno())

    def test_cli_version(self):
        result = subprocess.Popen(['ssm-version'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        self.assertFalse(error)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(output.strip('\n'), 'v{}'.format(__version__))

    def test_cli_version_full(self):
        result = subprocess.Popen(['ssm-version', '--full'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        self.assertFalse(error)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(output.strip('\n'), 'v{}-{}'.format(__version__, __build__ or get_buildno()))

    def test_cli_version_get_build(self):
        result = subprocess.Popen(['ssm-version', '--get-build'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = result.communicate()
        self.assertFalse(error)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(output.strip('\n'), get_buildno())