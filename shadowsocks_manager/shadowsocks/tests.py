# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

import json
import os
import time
import botocore
from abc import abstractmethod
from unittest import mock
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.core.management import call_command

from domain.models import Record
from domain.tests import AppTestCase as DomainAppTestCase
from notification.tests import AppTestCase as NotificationAppTestCase
from shadowsocks import models, serializers


import logging
# Get a logger for this django app
logger = logging.getLogger(__name__.split('.')[-2])
# Set the logging level to make the output clean
logger.setLevel(logging.CRITICAL)


import socket
def get_private_ip():
    """
    Get the private ip address.
    https://github.com/mayermakes/Get_IP
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    finally:
        s.close()
    return IP


"""
The following environment variables are required to run some of the tests:

  * SSM_TEST_SS_MGR_LOCALHOST=1     # run the tests for the ss-manager listening on localhost
  * SSM_TEST_SS_MGR_PRIVATE=1       # run the tests for the ss-manager listening on private ip

  If any of above environment variables is not set, the related tests will be skipped.
  For the enabled ss-manager interface, the corresponding ss-manager service should be running outside of the tests.

    * ss-manager --manager-address 127.0.0.1:$SSM_TEST_SS_MGR_PORT --executable /usr/local/bin/ss-server -m aes-256-gcm -s 127.0.0.1 -u
    * ss-manager --manager-address $SSM_TEST_SS_MGR_PRIVATE_IP:$SSM_TEST_SS_MGR_PORT --executable /usr/local/bin/ss-server -m aes-256-gcm -s $SSM_TEST_SS_MGR_PRIVATE_IP -u

    Note that the ss-server is binding to the same interface as the ss-manager in order to isolate the tests.
    The service requires the shadowsocks-libev edition rather than the shadowsocks-python edition.


The following environment variables are optional used to override the default values:

  * SSM_TEST_SS_MGR_PRIVATE_IP      # The private ip address of the ss-manager.
  * SSM_TEST_SS_MGR_PORT            # The port number of the ss-manager.
  * SSM_TEST_SS_PORT_BEGIN          # The beginning port number of the shadowsocks-libev edition manager.
  * SSM_TEST_SS_PORT_END            # The ending port number of the shadowsocks-libev edition manager.


Feature matrix for methods in unittest.TestCase class:
+-------------+------------------+---------------------+----------------+----------------------------------+---------------------------+
| Provider    | Method           | When is Called      | Class Method   | Manual Cleanup Needed            | When is Cleanup Done      |
+=============+==================+=====================+================+==================================+===========================+
| unittest    | setUp()          | Before each test    | No             | Yes                              | In tearDown()             |
|             |                  | method              |                |                                  |                           |
+-------------+------------------+---------------------+----------------+----------------------------------+---------------------------+
| unittest    | tearDown()       | After each test     | No             | N/A                              | N/A                       |
|             |                  | method              |                |                                  |                           |
+-------------+------------------+---------------------+----------------+----------------------------------+---------------------------+
| unittest    | setUpClass()     | Once before all     | Yes            | Yes                              | In tearDownClass()        |
|             |                  | tests in the class  |                |                                  |                           |
+-------------+------------------+---------------------+----------------+----------------------------------+---------------------------+
| unittest    | tearDownClass()  | Once after all      | Yes            | N/A                              | N/A                       |
|             |                  | tests in the class  |                |                                  |                           |
+-------------+------------------+---------------------+----------------+----------------------------------+---------------------------+

Feature matrix for methods in django.test.TestCase class:
+-------------+------------------+---------------------+----------------+----------------------------------+---------------------------+
| Provider    | Method           | When is Called      | Class Method   | Manual Cleanup Needed            | When is Cleanup Done      |
+=============+==================+=====================+================+==================================+===========================+
| django      | setUp()          | Before each test    | No             | No, Django rolls back database   | After each test method,   |
|             |                  | method              |                | changes                          | don't relay on tearDown() |
+-------------+------------------+---------------------+----------------+----------------------------------+---------------------------+
| django      | tearDown()       | After each test     | No             | N/A                              | N/A                       |
|             |                  | method              |                |                                  |                           |
+-------------+------------------+---------------------+----------------+----------------------------------+---------------------------+
| django      | setUpTestData()  | Once before all     | Yes            | No, Django rolls back database   | After each test method    |
|             |                  | tests in the class  |                | changes                          |                           |
+-------------+------------------+---------------------+----------------+----------------------------------+---------------------------+
"""

SS_MGR_LOCALHOST = os.getenv('SSM_TEST_SS_MGR_LOCALHOST')
SS_MGR_PRIVATE = os.getenv('SSM_TEST_SS_MGR_PRIVATE')
SS_MGR_PRIVATE_IP = os.getenv('SSM_TEST_SS_MGR_PRIVATE_IP') or get_private_ip()
SS_MGR_PORT = os.getenv('SSM_TEST_SS_MGR_PORT')
SS_PORT_BEGIN = os.getenv('SSM_TEST_SS_PORT_BEGIN')
SS_PORT_END = os.getenv('SSM_TEST_SS_PORT_END')


class BaseTestCase(TestCase):
    """
    A base test case for current app.
    This class is inherited from Django TestCase class, and provides the following features:

    Set a list of default fixtures for all test cases in this app.
    * fixtures = []

    Set a list of test case class names, if the up() and down() class methods are defined in
    the sub-class, all of them can be called at once by calling the allup() and alldown() class 
    methods in this class.
    * testcases = []
    """

    fixtures = []
    testcases = []

    class meta:
        abstract = True

    @classmethod
    @abstractmethod
    def up(cls):
        """
        Set up the test environment.
        """
        pass

    @classmethod
    @abstractmethod
    def down(cls):
        """
        Tear down the test environment.
        """
        pass

    @classmethod
    def allup(cls):
        """
        Call the up() class method (if exists) in each class defined in the testcases list.
        """
        for testcase in [globals().get(name) for name in cls.testcases]:
            method = getattr(testcase or {}, 'up', None)
            if method: method()

    @classmethod
    def alldown(cls):
        """
        Call the down() class method (if exists) in each class defined in the testcases list.
        """
        for testcase in [globals().get(name) for name in cls.testcases]:
            method = getattr(testcase or {}, 'down', None)
            if method: method()


class AppTestCase(BaseTestCase):
    fixtures = ['config.json']
    fixtures.extend(['auth.group.json'])
    fixtures.extend(DomainAppTestCase.fixtures)
    fixtures.extend(NotificationAppTestCase.fixtures)
    testcases = ['ConfigTestCase', 'AccountTestCase', 'NodeTestCase', 'SSManagerTestCase', 'NodeAccountTestCase', 'ManagementCommandTestCase']


class ConfigTestCase(AppTestCase):
    @classmethod
    def up(cls):
        obj = models.Config.load()
        if SS_PORT_BEGIN:
            obj.port_begin = int(SS_PORT_BEGIN)
        if SS_PORT_END:
            obj.port_end = int(SS_PORT_END)
        obj.save()

    @classmethod
    def setUpTestData(cls):
        cls.allup()

    def test_config_load(self):
        self.assertEqual(models.Config.load(), models.Config.objects.first())

    def test_config_serializer(self):
        obj = serializers.ConfigSerializer()
        json.loads(json.dumps(obj.to_representation(models.Config.objects.first())))


class AccountTestCase(AppTestCase):
    @classmethod
    def up(cls):
        config = models.Config.load()

        # generate 2 accounts
        for port in [config.port_begin, config.port_end]:
            models.Account(
                username=port,
                password='mock-password',
                email='mock@mock-example.com',
                first_name=str(port),
                last_name='mock',
                is_active=True,
            ).save()

    @classmethod
    def setUpTestData(cls):
        cls.allup()

    def test_account_clean_less(self):
        obj = models.Account.objects.first()
        obj.username = str(int(obj.username) - 1)  # set the port out of the config range
        self.assertRaises(ValidationError, obj.clean)

    def test_account_clean_great(self):
        obj = models.Account.objects.last()
        obj.username = str(int(obj.username) + 1)  # set the port out of the config range
        self.assertRaises(ValidationError, obj.clean)

    def test_account_port_accessible(self):
        # Perform the heartbeat once to recreate the ssmanager ports.
        # Seems that the rollback performed by django.test.TestCase.setUpTestData() method's isolation mechanism
        # doesn't trigger the django's signal mechanism, so the shadowsocks ports are not created.
        models.NodeAccount.heartbeat()

        for accout in models.Account.objects.all():
            for na in accout.nodes_ref.all():
                if na.node.ssmanager:
                    self.assertTrue(na.is_accessible)

    def test_account_port_accessible_ex(self):
        models.NodeAccount.heartbeat()

        for accout in models.Account.objects.all():
            for na in accout.nodes_ref.all():
                if na.node.ssmanager:
                    self.assertTrue(na.is_accessible_ex())

    def test_account_port_accessible_after_update(self):
        obj = models.Account.objects.first()
        obj.username = str(int(obj.username) + 1)
        obj.save()
        for na in obj.nodes_ref.all():
            if na.node.ssmanager:
                self.assertTrue(na.is_accessible)

    def test_account_port_accessible_ex_after_update(self):
        obj = models.Account.objects.first()
        obj.username = str(int(obj.username) + 1)
        obj.save()
        for na in obj.nodes_ref.all():
            if na.node.ssmanager:
                self.assertTrue(na.is_accessible_ex())

    def test_account_upadte_password(self):
        obj = models.Account.objects.first()
        obj.password = 'new-password'
        obj.save()
        for na in obj.nodes_ref.all():
            if na.node.ssmanager:
                ports = na.node.ssmanager.list()
                matching_port = next((port for port in ports if port['server_port'] == str(obj.username)), None)
                self.assertTrue(matching_port)
                self.assertEqual(matching_port['password'], 'new-password')

    def test_account_notify(self):
        for obj in models.Account.objects.all():
            self.assertTrue(obj.notify(sender=obj))

    def test_account_notify_validation_email(self):
        obj = models.Account.objects.first()
        obj.email = None
        self.assertRaisesRegex(ValidationError, 'email', obj.notify, sender=obj)

    def test_account_notify_validation_is_active(self):
        obj = models.Account.objects.first()
        obj.is_active = False
        self.assertRaisesRegex(ValidationError, 'is_active', obj.notify, sender=obj)

    def test_account_notify_validation_node(self):
        # make all nodes inactive
        for node in models.Node.objects.all():
            node.is_active = False
            node.save()
        obj = models.Account.objects.first()
        self.assertRaisesRegex(ValidationError, 'no active node', obj.notify, sender=obj)

    def test_account_notify_without_node_public_ip(self):
        # make all nodes' public_ip None
        for node in models.Node.objects.all():
            node.public_ip = None
            node.save()
        obj = models.Account.objects.first()
        self.assertTrue(obj.notify(sender=obj))

    def test_account_notify_without_node_record(self):
        # make all nodes' record None
        for node in models.Node.objects.all():
            node.record = None
            node.save()
        obj = models.Account.objects.first()
        self.assertTrue(obj.notify(sender=obj))

    def test_account_toggle_active(self):
        # make all accounts inactive
        for obj in models.Account.objects.all():
            obj.toggle_active()
            self.assertFalse(obj.is_active)

        # all nas are inactive now
        for na in models.NodeAccount.objects.all():
            self.assertFalse(na.is_active)

        # make all accounts active
        for obj in models.Account.objects.all():
            obj.toggle_active()
            self.assertTrue(obj.is_active)

        # all nas are active now
        for na in models.NodeAccount.objects.all():
            self.assertTrue(na.is_active)

    def test_account_serializer(self):
        obj = serializers.AccountSerializer()
        json.loads(json.dumps(obj.to_representation(models.Account.objects.first())))


class NodeTestCase(AppTestCase):
    @classmethod
    def up(cls):
        if SS_MGR_LOCALHOST == '1':
            # add a ss-libev node for the ssmanager listening on localhost
            models.Node(
                name='ss-libev-localhost',
                record=None,
                public_ip='127.0.0.1',
                private_ip='127.0.0.1',
                location='Local',
                sns_endpoint='arn:aws:sns:ap-northeast-1:0:topic', # mock sns endpoint
                sns_access_key='mock-sns_access_key',
                sns_secret_key='mock-sns_secret_key',
                is_active=True,
            ).save()

        if SS_MGR_PRIVATE == '1':
            # add a ss-libev node for the ssmanager listening on private ip
            DomainAppTestCase.allup()
            record = Record.objects.first()
            models.Node(
                name='ss-libev-private',
                record=record,
                public_ip=SS_MGR_PRIVATE_IP,
                private_ip=SS_MGR_PRIVATE_IP,
                location='Private',
                sns_endpoint='arn:aws:sns:ap-northeast-1:0:topic', # mock sns endpoint
                sns_access_key='mock-sns_access_key',
                sns_secret_key='mock-sns_secret_key',
                is_active=True,
            ).save()

    @classmethod
    def setUpTestData(cls):
        cls.allup()

    def test_node_str(self):
        for obj in models.Node.objects.all():
            self.assertEqual(str(obj), obj.__str__())

    def test_node_clean_positive(self):
        obj = models.Node()
        obj.record = Record()
        obj.public_ip = '0.0.0.0'
        obj.clean()

    def test_node_clean_negative(self):
        obj = models.Node()
        self.assertRaises(ValidationError, obj.clean)

    def test_node_sns_endpoint_region_positive(self):
        obj = models.Node()
        obj.sns_endpoint='arn:aws:sns:ap-northeast-1:0:topic'
        self.assertEqual(obj.sns_endpoint_region, 'ap-northeast-1')

    def test_node_sns_endpoint_region_negative_none(self):
        obj = models.Node()
        self.assertRaises(ValidationError, lambda: obj.sns_endpoint_region)

    def test_node_sns_endpoint_region_negative_syntax(self):
        obj = models.Node()
        obj.sns_endpoint='arn:aws:sns'
        self.assertRaises(ValidationError, lambda: obj.sns_endpoint_region)

    def test_node_is_matching_record_positive(self):
        for obj in models.Node.objects.filter(record__isnull=False):
            self.assertTrue(obj.is_matching_record)

    def test_node_is_matching_record_negative(self):
        for obj in models.Node.objects.filter(record__isnull=True):
            self.assertFalse(obj.is_matching_record)

    def test_node_is_matching_dns_query_negitive(self):
        for obj in models.Node.objects.all():
            self.assertFalse(obj.is_matching_dns_query)

    def test_node_is_port_open_timeout_local(self):
        config = models.Config.load()
        config.timeout_local = 0.5
        config.save()
        start_time = time.time()
        models.Node.is_port_open('10.0.0.255', 65000)
        end_time = time.time()
        elapsed_time = end_time - start_time
        # Assert that the elapsed time is approximately equal to the timeout
        self.assertAlmostEqual(elapsed_time, config.timeout_local, delta=0.1)

    def test_node_is_port_open_timeout_remote(self):
        config = models.Config.load()
        config.timeout_remote = 0.5
        config.save()
        start_time = time.time()
        models.Node.is_port_open('8.8.8.8', 65000)
        end_time = time.time()
        elapsed_time = end_time - start_time
        # Assert that the elapsed time is approximately equal to the timeout
        self.assertAlmostEqual(elapsed_time, config.timeout_remote, delta=0.1)

    def test_node_change_ip_negative(self):
        obj = models.Node.objects.first()
        self.assertRaises(botocore.exceptions.ClientError, obj.change_ip)

    def test_node_change_ips_negative(self):
        self.assertRaises(botocore.exceptions.ClientError, models.Node.change_ips)

    def test_node_toggle_active(self):
        # make all nodes inactive
        for obj in models.Node.objects.all():
            obj.toggle_active()
            self.assertFalse(obj.is_active)

        # all nas are inactive now
        for na in models.NodeAccount.objects.all():
            self.assertFalse(na.is_active)

        # make all nodes active
        for obj in models.Node.objects.all():
            obj.toggle_active()
            self.assertTrue(obj.is_active)

        # all nas are active now
        for na in models.NodeAccount.objects.all():
            self.assertTrue(na.is_active)

    def test_node_record_sync(self):
        # change nodes's public_ip
        for obj in models.Node.objects.filter(record__isnull=False):
            # plus 1 to the last part of public ip address
            obj.public_ip = '.'.join(obj.public_ip.split('.')[0:3] + [str(int(obj.public_ip.split('.')[-1]) + 1)])
            obj.save()
            self.assertTrue(obj.is_matching_record)

    def test_node_record_sync_after_toggle_active(self):
        # make nodes inactive
        for obj in models.Node.objects.filter(record__isnull=False):
            obj.toggle_active()
            self.assertTrue(obj.is_matching_record)

        # make nodes active
        for obj in models.Node.objects.filter(record__isnull=False):
            obj.toggle_active()
            self.assertTrue(obj.is_matching_record)

    def test_node_serializer(self):
        obj = serializers.NodeSerializer()
        json.loads(json.dumps(obj.to_representation(models.Node.objects.first())))


class NodeAccountTestCase(AppTestCase):
    @classmethod
    def up(cls):
        for account in models.Account.objects.all():
            account.add_all_nodes()

    @classmethod
    def setUpTestData(cls):
        cls.allup()

    def test_nodeaccount_str(self):
        for obj in models.NodeAccount.objects.all():
            self.assertEqual(str(obj), obj.__str__())

    def test_nodeaccount_on_update_without_ssmanager(self):
        # Django 5 forbids using unsaved instances as foreign keys. Save a bare
        # Node (no related SSManager) to preserve the "without ssmanager" intent.
        node = models.Node.objects.create(name='no-ssmgr-on-update')
        account = models.Account.objects.first()
        obj = models.NodeAccount(node=node, account=account)
        obj.on_update()

    def test_nodeaccount_on_update_with_ssmanager_inaccessible(self):
        for obj in models.NodeAccount.objects.all():
            if obj.node.ssmanager:
                ssmanager = obj.node.ssmanager
                ssmanager.port = 65000
                ssmanager.save()
                obj.on_update()

    def test_nodeaccount_on_delete_without_ssmanager(self):
        # Django 5 forbids using unsaved instances as foreign keys. Save a bare
        # Node (no related SSManager) to preserve the "without ssmanager" intent.
        node = models.Node.objects.create(name='no-ssmgr-on-delete')
        account = models.Account.objects.first()
        obj = models.NodeAccount(node=node, account=account)
        obj.on_delete()

    def test_nodeaccount_on_delete_with_ssmanager_inaccessible(self):
        for obj in models.NodeAccount.objects.all():
            if obj.node.ssmanager:
                ssmanager = obj.node.ssmanager
                ssmanager.port = 65000
                ssmanager.save()
                obj.on_delete()

    def test_nodeaccount_is_accessible_positive(self):
        models.NodeAccount.heartbeat()
        for obj in models.NodeAccount.objects.all():
            if obj.node.ssmanager:
                self.assertTrue(obj.is_accessible)

    def test_nodeaccount_is_accessible_ex_positive(self):
        models.NodeAccount.heartbeat()
        for obj in models.NodeAccount.objects.all():
            if obj.node.ssmanager:
                self.assertTrue(obj.is_accessible_ex())
                # should hit cache
                self.assertTrue(obj.is_accessible_ex())

    def test_nodeaccount_cache(self):
        obj = models.NodeAccount.objects.first()
        if obj.node.ssmanager:
            obj.is_accessible_ex()
            self.assertTrue(models.cache.get('{}:{}'.format(obj.node.public_ip, obj.account.username)))
            obj.delete()
            self.assertFalse(models.cache.get('{}:{}'.format(obj.node.public_ip, obj.account.username)))

    def test_nodeaccount_is_created_positive(self):
        models.NodeAccount.heartbeat()
        for obj in models.NodeAccount.objects.all():
            if obj.node.ssmanager:
                self.assertTrue(obj.is_created())

    def test_nodeaccount_is_created_positive_original(self):
        models.NodeAccount.heartbeat()
        for obj in models.NodeAccount.objects.all():
            if obj.node.ssmanager:
                obj.account.username = str(int(obj.account.username) + 1)
                self.assertTrue(obj.is_created(original=True))
    
    def test_nodeaccount_is_created_negative(self):
        # Django 5 forbids using unsaved instances as foreign keys. Save a bare
        # Node (no related SSManager) to preserve the "without ssmanager" intent.
        node = models.Node.objects.create(name='no-ssmgr-is-created-neg')
        account = models.Account.objects.first()
        obj = models.NodeAccount(node=node, account=account)
        self.assertEqual(obj.is_created(), None)

    def test_nodeaccount_serializer(self):
        obj = serializers.NodeAccountSerializer()
        json.loads(json.dumps(obj.to_representation(models.NodeAccount.objects.first())))


class SSManagerTestCase(AppTestCase):
    @classmethod
    def up(cls):
        if SS_MGR_LOCALHOST == '1':
            ssmanager = models.SSManager(
                node=models.Node.objects.get(name='ss-libev-localhost'),
                interface=models.InterfaceList.LOCALHOST,
                encrypt='aes-256-gcm',
                server_edition=models.ServerEditionList.LIBEV,
                is_v2ray_enabled=False,
            )
            if SS_MGR_PORT:
                ssmanager.port = int(SS_MGR_PORT)
            ssmanager.save()

        if SS_MGR_PRIVATE == '1':
            ssmanager = models.SSManager(
                node=models.Node.objects.get(name='ss-libev-private'),
                interface=models.InterfaceList.PRIVATE,
                encrypt='aes-256-gcm',
                server_edition=models.ServerEditionList.LIBEV,
                is_v2ray_enabled=False,
            )
            if SS_MGR_PORT:
                ssmanager.port = int(SS_MGR_PORT)
            ssmanager.save()

    @classmethod
    def setUpTestData(cls):
        cls.allup()

    def test_ssmanager_is_accessible(self):
        for obj in models.SSManager.objects.all():
            self.assertTrue(obj.is_accessible)

    def test_ssmanager_add_and_remove(self):
        for obj in models.SSManager.objects.all():
            port=8388
            obj.add(port, 'mock-password')
            self.assertTrue(obj.is_port_created_or_accessible(port))

            obj.remove(port)
            self.assertFalse(obj.is_port_created_or_accessible(port))

    def test_ssmanager_clean(self):
        for obj in models.SSManager.objects.filter(interface=models.InterfaceList.PRIVATE):
            obj.node.private_ip = None
            self.assertRaises(ValidationError, obj.clean)

    def test_ssmanager_connect_timeout_local(self):
        config = models.Config.load()
        config.timeout_local = 0.5
        config.save()
        obj = models.SSManager(node=models.Node(private_ip='10.0.0.255', public_ip='8.8.8.8'), port=65000)
        start_time = time.time()
        obj._ping()
        end_time = time.time()
        elapsed_time = end_time - start_time
        self.assertAlmostEqual(elapsed_time, config.timeout_local, delta=0.1)

    def test_ssmanager_connect_timeout_remote(self):
        config = models.Config.load()
        config.timeout_remote = 0.5
        config.save()
        obj = models.SSManager(node=models.Node(private_ip='10.0.0.255', public_ip='8.8.8.8'), port=65000, interface=models.InterfaceList.PUBLIC)
        start_time = time.time()
        obj._ping()
        end_time = time.time()
        elapsed_time = end_time - start_time
        self.assertAlmostEqual(elapsed_time, config.timeout_local, delta=0.1)

    def test_ssmanager_is_port_created_unknown(self):
        obj = models.SSManager(node=models.Node(private_ip='10.0.0.255', public_ip='8.8.8.8'), port=65000)
        self.assertEqual(obj.is_port_created(8388), None)

    def test_ssmanager_get_nodeaccount_negative_account(self):
        obj = models.SSManager(node=models.Node())
        self.assertRaises(models.Account.DoesNotExist, obj.get_nodeaccount, 8388)

    def test_ssmanager_get_nodeaccount_negative_nodeaccount(self):
        # Django 5 forbids passing unsaved instances to related filters
        # (NodeAccount.objects.filter(node=node) inside get_nodeaccount).
        # Save the Node (no SSManager attached so it has no NodeAccount).
        account = models.Account.objects.first()
        node = models.Node.objects.create(name='no-ssmgr-get-na-neg')
        obj = models.SSManager(node=node)
        self.assertRaises(models.NodeAccount.DoesNotExist, obj.get_nodeaccount, account.username)

    def test_ssmanager_cache(self):
        obj = models.SSManager.objects.first()
        if obj:
            obj.list_ex()
            self.assertTrue(models.cache.get('{}-{}'.format(obj, 'list')))
            obj.delete()
            self.assertFalse(models.cache.get('{}-{}'.format(obj, 'list')))

    def test_ssmanager_serializer(self):
        serializer = serializers.SSManagerSerializer()
        for obj in models.SSManager.objects.all():
            json.loads(json.dumps(serializer.to_representation(obj)))


class ManagementCommandTestCase(AppTestCase):

    def test_cmd_shadowsocks_config_port_begin(self):
        call_command('shadowsocks_config', '--port-begin', '65001')
        self.assertEqual(models.Config.load().port_begin, 65001)

    def test_cmd_shadowsocks_config_port_enc(self):
        call_command('shadowsocks_config', '--port-end', '65002')
        self.assertEqual(models.Config.load().port_end, 65002)

    def test_cmd_shadowsocks_config_timeout_remote(self):
        call_command('shadowsocks_config', '--timeout-remote', '0.9')
        self.assertEqual(models.Config.load().timeout_remote, 0.9)

    def test_cmd_shadowsocks_config_timeout_local(self):
        call_command('shadowsocks_config', '--timeout-local', '0.9')
        self.assertEqual(models.Config.load().timeout_local, 0.9)

    def test_cmd_shadowsocks_config_cache_timeout(self):
        call_command('shadowsocks_config', '--cache-timeout', '99')
        self.assertEqual(models.Config.load().cache_timeout, 99)


class NodeOriginalSnapshotTestCase(AppTestCase):
    """
    Regression tests for the `_original_*` field-snapshot tracking on the
    Node model.

    Background: Node.__init__ captures `_original_is_active` and
    `_original_public_ip` so that `Node.on_update()` can detect "activity
    changed" and cascade is_active to all NodeAccount rows. Prior to the
    `save()` override + `_snapshot_original()` helper, the snapshot was
    only refreshed at __init__ — so a second `save()` on the SAME
    in-memory instance compared the new value against the *construction-
    time* original, not the *just-written* DB value. That broke the
    cascade in `Node.change_ips_softly()` step-5 reactivation when the
    AWS Config event arrived after the 60s sleep instead of during it,
    leaving NodeAccount rows permanently inactive after a rotation.
    """

    def _make_account(self, username='9001'):
        return models.Account.objects.create(
            username=username,
            password='unit-test-pw',
            is_active=True,
        )

    def _make_node(self, name='unit-test-node'):
        # Use a public_ip that won't accidentally hit a real service.
        return models.Node.objects.create(
            name=name,
            public_ip='192.0.2.1',  # TEST-NET-1, RFC 5737
            private_ip='10.255.255.255',
            location='Unit Test',
            sns_endpoint='arn:aws:sns:ap-northeast-1:0:topic',
            sns_access_key='mock',
            sns_secret_key='mock',
            is_active=True,
        )

    def test_node_init_snapshots_original(self):
        """After loading a Node from DB, _original_* mirrors stored values."""
        n = self._make_node()
        loaded = models.Node.objects.get(pk=n.pk)
        self.assertEqual(loaded._original_is_active, loaded.is_active)
        self.assertEqual(loaded._original_public_ip, loaded.public_ip)

    def test_node_save_refreshes_snapshot(self):
        """After save(), _original_* must reflect the just-written values, not
        the construction-time values. This is the core invariant the fix adds."""
        n = self._make_node()
        # Modify both tracked fields and save.
        n.is_active = False
        n.public_ip = '192.0.2.2'
        n.save()
        self.assertEqual(n._original_is_active, False,
            '_original_is_active should be refreshed to the just-saved value')
        self.assertEqual(n._original_public_ip, '192.0.2.2',
            '_original_public_ip should be refreshed to the just-saved value')

    def test_node_toggle_twice_on_same_instance_cascades_to_nodeaccount(self):
        """The regression test for the change_ips_softly bug.

        Toggling Node.is_active twice on the SAME in-memory instance must
        cascade NodeAccount.is_active twice — once OFF, once back ON. The
        bug pre-fix was that the second toggle's on_update() compared
        against a stale construction-time _original and skipped the cascade.
        """
        node = self._make_node()
        account = self._make_account('9001')
        na = models.NodeAccount.objects.create(node=node, account=account, is_active=True)

        # Step 1: simulate `node.toggle_active()` → deactivate.
        node.is_active = False
        node.save()
        na.refresh_from_db()
        self.assertFalse(na.is_active,
            'first toggle should cascade NodeAccount.is_active to False')

        # Step 2: simulate `node.toggle_active()` → reactivate, on the SAME instance.
        node.is_active = True
        node.save()
        na.refresh_from_db()
        self.assertTrue(na.is_active,
            'second toggle on the same instance must also cascade — '
            'this is the change_ips_softly regression we are guarding against')

    def test_node_toggle_twice_respects_account_is_active(self):
        """Cascade computes `new = node.is_active AND account.is_active`.
        When the account is inactive, NodeAccount stays False even after
        toggling the node back to active.
        """
        node = self._make_node()
        account = self._make_account('9002')
        account.is_active = False
        account.save()
        na = models.NodeAccount.objects.create(node=node, account=account, is_active=False)

        node.is_active = False
        node.save()
        na.refresh_from_db()
        self.assertFalse(na.is_active)

        node.is_active = True
        node.save()
        na.refresh_from_db()
        self.assertFalse(na.is_active,
            'reactivating the node should NOT reactivate NodeAccount '
            'when the underlying Account is inactive')

    def test_node_no_change_no_cascade(self):
        """Saving without changing is_active should not flip the
        NodeAccount cascade (no spurious post_save side effects)."""
        node = self._make_node()
        account = self._make_account('9003')
        na = models.NodeAccount.objects.create(node=node, account=account, is_active=True)

        # Save with no change to is_active.
        node.public_ip = '192.0.2.3'
        node.save()
        na.refresh_from_db()
        self.assertTrue(na.is_active,
            'a save that does not flip is_active should leave NodeAccount untouched')


class NodeChangeIpsSoftlyTestCase(AppTestCase):
    """Resilience tests for Node.change_ips_softly().

    The soft-rotation loop inactivates a node, waits for the DNS TTL,
    triggers the IP change, then reactivates it. The hardening guards two
    failure modes seen in the IP-rotation incident:

      1. If change_ip() (or anything in the cycle) raises, a finally block
         must restore is_active=True so the node isn't left permanently
         inactive — which also drops it from the next run's eligibility
         filter, compounding the outage.
      2. Each node is re-loaded and re-checked inside the loop, so a node
         whose SNS credentials are blank is skipped instead of having a
         rotation triggered against stale state.
    """

    def _make_node(self, name='soft-rotate-node', **kwargs):
        defaults = dict(
            public_ip='192.0.2.10',  # TEST-NET-1, RFC 5737
            private_ip='10.255.255.254',
            location='Unit Test',
            sns_endpoint='arn:aws:sns:ap-northeast-1:0:topic',
            sns_access_key='mock',
            sns_secret_key='mock',
            is_active=True,
        )
        defaults.update(kwargs)
        return models.Node.objects.create(name=name, **defaults)

    def test_restores_is_active_when_change_ip_raises(self):
        """change_ip() failing mid-cycle must leave the node ACTIVE.

        This is the core regression: pre-fix, an exception after the node
        was inactivated left is_active=False permanently.
        """
        node = self._make_node()
        with mock.patch('shadowsocks.models.time.sleep'), \
                mock.patch.object(models.Node, 'change_ip',
                                  side_effect=RuntimeError('boom')) as m_change_ip:
            # The exception propagates out of the loop, but the finally block
            # must already have restored is_active before it does.
            with self.assertRaises(RuntimeError):
                models.Node.change_ips_softly()
        m_change_ip.assert_called_once()
        node.refresh_from_db()
        self.assertTrue(node.is_active,
            'a change_ip() failure must not leave the node stuck inactive')

    def test_happy_path_keeps_node_active(self):
        """On success the node is rotated once and left active."""
        node = self._make_node()
        with mock.patch('shadowsocks.models.time.sleep'), \
                mock.patch.object(models.Node, 'change_ip') as m_change_ip:
            models.Node.change_ips_softly()
        m_change_ip.assert_called_once()
        node.refresh_from_db()
        self.assertTrue(node.is_active)

    def test_skips_node_with_blank_credentials(self):
        """A node whose SNS credentials are blank is selected by the
        not-null filter but skipped by the in-loop guard — change_ip is
        never called and the node is left untouched (active)."""
        node = self._make_node(name='blank-creds',
                               sns_access_key='', sns_secret_key='')
        with mock.patch('shadowsocks.models.time.sleep'), \
                mock.patch.object(models.Node, 'change_ip') as m_change_ip:
            models.Node.change_ips_softly()
        m_change_ip.assert_not_called()
        node.refresh_from_db()
        self.assertTrue(node.is_active)
