# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

import json
import os
from abc import abstractmethod
from django.test import TestCase
from django.core.exceptions import ValidationError

from domain.models import Record
from domain.tests import AppTestCase as DomainAppTestCase
from notification.tests import AppTestCase as NotificationAppTestCase
from shadowsocks import models, serializers


import logging
# Get a logger for this django app
logger = logging.getLogger(__name__.split('.')[-2])
# Set the logging level to make the output clean
logger.setLevel(logging.ERROR)


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
    testcases = ['ConfigTestCase', 'AccountTestCase', 'NodeTestCase', 'SSManagerTestCase', 'NodeAccountTestCase']


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

    def test_node_is_matching_record_positive(self):
        for obj in models.Node.objects.filter(record__isnull=False):
            self.assertTrue(obj.is_matching_record)

    def test_node_is_matching_record_negative(self):
        for obj in models.Node.objects.filter(record__isnull=True):
            self.assertFalse(obj.is_matching_record)

    def test_node_is_matching_dns_query_negitive(self):
        for obj in models.Node.objects.all():
            self.assertFalse(obj.is_matching_dns_query)

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
            node = models.Node.objects.filter(name='ss-libev-localhost').first()
            if node:
                na = models.NodeAccount(node=node, account=account, is_active=(account.is_active and node.is_active))
                na.save()

            node = models.Node.objects.filter(name='ss-libev-private').first()
            if node:
                na = models.NodeAccount(node=node, account=account, is_active=(account.is_active and node.is_active))
                na.save()
        
    @classmethod
    def setUpTestData(cls):
        cls.allup()

    def test_nodeaccount_is_accessible_positive(self):
        #models.NodeAccount.heartbeat()
        for obj in models.NodeAccount.objects.all():
            if obj.node.ssmanager:
                self.assertTrue(obj.is_accessible)

    def test_nodeaccount_is_accessible_ex_positive(self):
        #models.NodeAccount.heartbeat()
        for obj in models.NodeAccount.objects.all():
            if obj.node.ssmanager:
                self.assertTrue(obj.is_accessible_ex())

    def test_nodeaccount_is_created(self):
        for obj in models.NodeAccount.objects.all():
            if obj.node.ssmanager:
                self.assertTrue(obj.is_created())

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

    def test_ssmanager_serializer(self):
        serializer = serializers.SSManagerSerializer()
        for obj in models.SSManager.objects.all():
            json.loads(json.dumps(serializer.to_representation(obj)))
