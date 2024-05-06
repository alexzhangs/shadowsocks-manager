# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

import json
import re
from abc import abstractmethod
from django.test import TestCase
from django.core.exceptions import ValidationError

from domain.models import Record
from domain.tests import AppTestCase as DomainAppTestCase
from notification.tests import AppTestCase as NotificationAppTestCase
from shadowsocks import models, serializers


import logging
# Get a logger for this module
logger = logging.getLogger(__name__)
# Set the logging level to make the output clean
logger.setLevel(logging.ERROR)


import socket
def get_local_ip():
    """
    Get the local ip address.
    https://github.com/mayermakes/Get_IP
    """
    ip = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        ip.connect(('10.255.255.255', 1))
        IP = ip.getsockname()[0]
    except:
        raise
    finally:
        ip.close()
    return IP
local_ip = get_local_ip()


"""
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
    fixtures.extend(['fixtures/auth.group.json'])
    fixtures.extend(DomainAppTestCase.fixtures)
    fixtures.extend(NotificationAppTestCase.fixtures)
    testcases = ['ConfigTestCase', 'AccountTestCase', 'NodeTestCase', 'SSManagerTestCase', 'NodeAccountTestCase']


class ConfigTestCase(AppTestCase):
    @classmethod
    def up(cls):
        obj = models.Config.load()
        obj.timeout_local=0.3
        obj.timeout_remote=1  # minimal the waiting time with mock public ip address
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
                self.assertTrue(na.is_accessible)

    def test_account_port_accessible_ex(self):
        models.NodeAccount.heartbeat()

        for accout in models.Account.objects.all():
            for na in accout.nodes_ref.all():
                self.assertTrue(na.is_accessible_ex())

    def test_account_port_accessible_after_update(self):
        obj = models.Account.objects.first()
        obj.username = str(int(obj.username) + 1)
        obj.save()
        for na in obj.nodes_ref.all():
            self.assertTrue(na.is_accessible)

    def test_account_port_accessible_ex_after_update(self):
        obj = models.Account.objects.first()
        obj.username = str(int(obj.username) + 1)
        obj.save()
        for na in obj.nodes_ref.all():
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

        # add a ss-libev node for the ssmanager listening on private ip
        models.Node(
            name='ss-libev-private',
            record=None,
            public_ip=local_ip,
            private_ip=local_ip,
            location='Private',
            sns_endpoint='arn:aws:sns:ap-northeast-1:0:topic', # mock sns endpoint
            sns_access_key='mock-sns_access_key',
            sns_secret_key='mock-sns_secret_key',
            is_active=True,
        ).save()

        DomainAppTestCase.allup()
        record = Record.objects.first()
        # add a ss-libev node for the ssmanager listening on public ip
        models.Node(
            name='ss-libev-public',
            record=record,
            public_ip=local_ip,  # using private ip as public ip
            private_ip=local_ip,
            location='Public',
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
        # Add the first account to the localhost node and the private node
        account = models.Account.objects.all().first()
        node = models.Node.objects.get(name='ss-libev-localhost')
        na = models.NodeAccount(node=node, account=account, is_active=(account.is_active and node.is_active))
        na.save()

        node = models.Node.objects.get(name='ss-libev-private')
        na = models.NodeAccount(node=node, account=account, is_active=(account.is_active and node.is_active))
        na.save()
        
        # Add the last account to the public node
        # The public node is using the private ip to mock public ip, using different account to avoid the port conflict
        account = models.Account.objects.all().last()
        node = models.Node.objects.get(name='ss-libev-public')
        na = models.NodeAccount(node=node, account=account, is_active=(account.is_active and node.is_active))
        na.save()

    @classmethod
    def setUpTestData(cls):
        cls.allup()

    def test_nodeaccount_is_accessible_positive(self):
        #models.NodeAccount.heartbeat()
        for obj in models.NodeAccount.objects.all():
            self.assertTrue(obj.is_accessible)

    def test_nodeaccount_is_accessible_ex_positive(self):
        #models.NodeAccount.heartbeat()
        for obj in models.NodeAccount.objects.all():
            self.assertTrue(obj.is_accessible_ex())

    def test_nodeaccount_is_created(self):
        for obj in models.NodeAccount.objects.all():
            self.assertTrue(obj.is_created())

    def test_nodeaccount_serializer(self):
        obj = serializers.NodeAccountSerializer()
        json.loads(json.dumps(obj.to_representation(models.NodeAccount.objects.first())))


class SSManagerTestCase(AppTestCase):
    @classmethod
    def up(cls):
        # Add a libev edition manager to the localhost node
        # Make sure this manager is running and accessible at localhost before the test.
        # Example command:
        # MGR_PORT=6001 SS_PORTS=8381-8479 ENCRYPT=aes-256-cfb
        # docker run -d -p 127.0.0.1:$MGR_PORT:$MGR_PORT/UDP -p 127.0.0.1:$SS_PORTS:$SS_PORTS/UDP -p 127.0.0.1:$SS_PORTS:$SS_PORTS \
        #   --name ssm-ss-libev-localhost shadowsocks/shadowsocks-libev:edge \
        #   ss-manager --manager-address 0.0.0.0:$MGR_PORT --executable /usr/local/bin/ss-server -m $ENCRYPT -s 0.0.0.0 -u

        models.SSManager(
            node=models.Node.objects.get(name='ss-libev-localhost'),
            interface=models.InterfaceList.LOCALHOST,
            port=6001,
            encrypt='aes-256-cfb',
            server_edition=models.ServerEditionList.LIBEV,
            is_v2ray_enabled=False,
        ).save()

        # Add a libev edition manager to the private node
        # Make sure this manager is running and accessible at private ip before the test.
        # Example command:
        # MGR_PORT=6002 SS_PORTS=8381-8479 ENCRYPT=aes-256-cfb
        # docker run -d -p <private_ip>:$MGR_PORT:$MGR_PORT/UDP -p <private_ip>:$SS_PORTS:$SS_PORTS/UDP -p <private_ip>:$SS_PORTS:$SS_PORTS \
        #   --name ssm-ss-libev-private shadowsocks/shadowsocks-libev:edge \
        #   ss-manager --manager-address 0.0.0.0:$MGR_PORT --executable /usr/local/bin/ss-server -m $ENCRYPT -s 0.0.0.0 -u
        models.SSManager(
            node=models.Node.objects.get(name='ss-libev-private'),
            interface=models.InterfaceList.PRIVATE,
            port=6002,
            encrypt='aes-256-cfb',
            server_edition=models.ServerEditionList.LIBEV,
            is_v2ray_enabled=False,
        ).save()

        # Add a libev edition manager to the public node
        # Make sure this manager is running and accessible at private ip before the test.
        # Example command:
        # MGR_PORT=6003 SS_PORTS=8480 ENCRYPT=aes-256-cfb
        # docker run -d -p <private_ip>:$MGR_PORT:$MGR_PORT/UDP -p <private_ip>:$SS_PORTS:$SS_PORTS/UDP -p <private_ip>:$SS_PORTS:$SS_PORTS \
        #   --name ssm-ss-libev-public shadowsocks/shadowsocks-libev:edge \
        #   ss-manager --manager-address 0.0.0.0:$MGR_PORT --executable /usr/local/bin/ss-server -m $ENCRYPT -s 0.0.0.0 -u
        models.SSManager(
            node=models.Node.objects.get(name='ss-libev-public'),
            interface=models.InterfaceList.PUBLIC,
            port=6003,
            encrypt='aes-256-cfb',
            server_edition=models.ServerEditionList.LIBEV,
            is_v2ray_enabled=False,
        ).save()

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
        obj = models.SSManager.objects.filter(interface=models.InterfaceList.PUBLIC).first()
        obj.node.public_ip = None
        self.assertRaises(ValidationError, obj.clean)

    def test_ssmanager_serializer(self):
        obj = serializers.SSManagerSerializer()
        json.loads(json.dumps(obj.to_representation(models.SSManager.objects.first())))
