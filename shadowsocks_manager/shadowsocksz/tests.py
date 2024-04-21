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
from shadowsocksz import models, serializers


import logging
# disable logging for the test module to make the output clean
logging.disable(logging.CRITICAL)


import socket
def get_ip():
    """
    Get the local ip address.
    https://github.com/mayermakes/Get_IP
    """
    ip = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        ip.connect(('10.255.255.255', 1))
        IP = ip.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        ip.close()
    return IP
ip = get_ip()


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
            obj = models.Account(
                username=port,
                password='mock-password',
                email='mock@mock-example.com',
                first_name=str(port),
                last_name='mock',
                is_active=True,
            )
            obj.save()

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
        # The ssserver's live ports are affected by the ssmanager's restart comes from the other test cases.
        # Perform the heartbeat once to recreate the ssmanager ports.
        # Seems that the rollback performed by django.test.TestCase.setUpTestData() method's isolation mechanism
        # doesn't trigger the django's signal mechanism, so the ssserver ports are not created.
        models.NodeAccount.heartbeat()

        for obj in models.Account.objects.all():
            self.assertTrue(obj.nodes_ref.get(node__name='localhost').is_accessible_ex())

    def test_account_port_accessible_after_update(self):
        obj = models.Account.objects.first()
        obj.username = str(int(obj.username) + 1)
        obj.save()
        self.assertTrue(obj.nodes_ref.get(node__name='localhost').is_accessible_ex())

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


class NodeTestCase(AppTestCase):
    @classmethod
    def up(cls):
        DomainAppTestCase.allup()
        record = Record.objects.first()

        # generate one localhost node
        obj = models.Node(
            name='localhost',
            record=None,
            public_ip=ip,
            private_ip=ip,
            location='Local',
            sns_endpoint=None,
            sns_access_key=None,
            sns_secret_key=None,
            is_active=True,
        )
        obj.save()

        # generate 2 mock nodes
        for i in list(range(1, 3)):
            obj = models.Node(
                name='mock-node-{}'.format(i),
                record=record,
                public_ip='.'.join([str(i) for j in list(range(4))]), # mock ip address here
                private_ip=ip,
                location='mock-locaction-{}'.format(i),
                sns_endpoint='arn:aws:sns:ap-northeast-1:{}:topic'.format(i), # mock sns endpoint
                sns_access_key='mock-sns_access_key-{}'.format(i),
                sns_secret_key='mock-sns_secret_key-{}'.format(i),
                is_active=True,
            )
            obj.save()

    @classmethod
    def setUpTestData(cls):
        cls.allup()

    def test_node_is_matching_record(self):
        for obj in models.Node.objects.all():
            if obj.record:
                self.assertTrue(obj.is_matching_record)
            else:
                self.assertFalse(obj.is_matching_record)

    def test_node_is_matching_dns_query(self):
        for obj in models.Node.objects.all():
            self.assertFalse(obj.is_matching_dns_query)

    def test_node_record_sync(self):
        # ip addresses are synced between node and record
        for obj in models.Node.objects.filter(record__isnull=False):
            self.assertTrue(obj.is_matching_record)

    def test_node_toggle_active(self):
        # all nas are active before test
        for na in models.NodeAccount.objects.all():
            self.assertTrue(na.is_active)

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
            obj.public_ip = '.'.join(str(int(part)+100) for part in obj.public_ip.split('.'))
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
        # add the localhost node to all accounts
        for account in models.Account.objects.all():
            node = models.Node.objects.get(name='localhost')
            if models.NodeAccount.objects.filter(node=node, account=account).count() == 0:
                na = models.NodeAccount(node=node, account=account, is_active=(account.is_active and node.is_active))
                na.save()

    @classmethod
    def setUpTestData(cls):
        cls.allup()

    def test_nodeaccount_is_accessible_positive(self):
        models.NodeAccount.heartbeat()
        # get the nas that have node.ssmanager listening on localhost
        for obj in models.NodeAccount.objects.filter(node__ssmanagers__interface=models.InterfaceList.LOCALHOST):
            self.assertTrue(obj.is_accessible_ex())

    def test_nodeaccount_is_accessible_negative(self):
        # get the nas that don't have node.ssmanager listening on localhost
        for obj in models.NodeAccount.objects.exclude(node__ssmanagers__interface=models.InterfaceList.LOCALHOST):
            self.assertFalse(obj.is_accessible_ex())

    def test_nodeaccount_is_created(self):
        # get the nas that have node.ssmanager listening on localhost
        for obj in models.NodeAccount.objects.filter(node__ssmanagers__interface=models.InterfaceList.LOCALHOST):
            # the Shadowsocks python edition's list command doesn't work, so the is_created() method is always None
            self.assertFalse(obj.is_created())

    def test_nodeaccount_serializer(self):
        obj = serializers.NodeAccountSerializer()
        json.loads(json.dumps(obj.to_representation(models.NodeAccount.objects.first())))


class SSManagerTestCase(AppTestCase):
    @classmethod
    def up(cls):
        # add a ssmanager to localhost node, using python edition, auto install&start
        obj = models.SSManager(
            node=models.Node.objects.get(name='localhost'),
            interface=models.InterfaceList.LOCALHOST,
            port=6001,
            fastopen=False,
            encrypt='aes-256-cfb',
            server_edition=models.ServerEditionList.PYTHON,
            is_v2ray_enabled=False,
            is_server_enabled=True,
        )
        obj.save()

        # add a ssmanager to each mock node, using libev edition
        for node in models.Node.objects.exclude(name='localhost'):
            obj = models.SSManager(
                node=node,
                interface=node.pk % 2 + 2,  # limit the interface within: [2, 3]
                port=6001,
                fastopen=False,
                encrypt='aes-256-cfb',
                server_edition=models.ServerEditionList.LIBEV,
                is_v2ray_enabled=False,
            )
            obj.save()

    @classmethod
    def setUpTestData(cls):
        cls.allup()

    def test_ssmanager_is_accessible(self):
        obj = models.SSManager.objects.filter(interface=models.InterfaceList.LOCALHOST).first()
        self.assertTrue(obj.is_accessible)

    def test_ssmanager_is_server_enabled(self):
        obj = models.SSManager.objects.filter(interface=models.InterfaceList.LOCALHOST).first()
        self.assertTrue(obj.is_server_enabled)

    def test_ssmanager_server_version(self):
        obj = models.SSManager.objects.filter(interface=models.InterfaceList.LOCALHOST).first()
        #self.assertTrue(obj.server.version)

    def test_ssmanager_server_status(self):
        obj = models.SSManager.objects.filter(interface=models.InterfaceList.LOCALHOST).first()
        self.assertTrue(re.match('(running|sleeping)', obj.server.status or ''))

    def test_ssmanager_add_and_remove(self):
        obj = models.SSManager.objects.filter(interface=models.InterfaceList.LOCALHOST).first()
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
