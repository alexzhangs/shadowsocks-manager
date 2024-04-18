# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

import json
from django.test import TestCase
from django.core.exceptions import ValidationError
from botocore.exceptions import ClientError

from domain.models import Record
from domain.tests import DomainTestCase
from notification.tests import NotificationTestCase
from shadowsocks import models, serializers


# https://github.com/mayermakes/Get_IP
import socket
def get_ip():
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


# Create your tests here.
class AllData:
    fixtures = ['config.json', 'fixtures/auth.group.json']
    fixtures.extend(DomainTestCase.fixtures)
    fixtures.extend(NotificationTestCase.fixtures)
    testcases = ['ConfigTestCase', 'AccountTestCase', 'NodeTestCase', 'SSManagerTestCase', 'NodeAccountTestCase']

    @classmethod
    def up(cls):
        for testcase in [globals().get(name) for name in cls.testcases]:
            method = getattr(testcase or {}, 'up', None)
            if method: method()

    @classmethod
    def down(cls):
        for testcase in [globals().get(name) for name in cls.testcases]:
            method = getattr(testcase or {}, 'down', None)
            if method: method()


class ConfigTestCase(TestCase):
    fixtures = ['config.json']

    @classmethod
    def up(cls):
        print('Config: loading data ...')
        obj = models.Config.load()
        obj.timeout_local=0.3
        obj.timeout_remote=1  # minimal the waiting time with mock public ip address
        obj.save()

    def setUp(self):
        self.up()

    def test(self):
        print('testing Config load() ...')
        self.assertEqual(models.Config.load(), models.Config.objects.first())

    def test_serializer(self):
        print('testing Config serializer ...')
        obj = serializers.ConfigSerializer()
        json.loads(json.dumps(obj.to_representation(models.Config.objects.first())))


class AccountTestCase(TestCase):
    fixtures = AllData.fixtures

    @classmethod
    def up(cls):
        print('Account: loading data ...')
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

    def setUp(self):
        AllData.up()

    def tearDown(self):
        AllData.down()
        super(AccountTestCase, self).tearDown()

    def test(self):
        print('testing Account clean() ...')
        obj = models.Account.objects.first()
        obj.username = str(int(obj.username) - 1)  # set the port out of the config range
        self.assertRaises(ValidationError, obj.clean)

        obj = models.Account.objects.last()
        obj.username = str(int(obj.username) + 1)  # set the port out of the config range
        self.assertRaises(ValidationError, obj.clean)

        print('testing Account port status ...')
        for obj in models.Account.objects.all():
            self.assertTrue(obj.nodes_ref.get(node__name='localhost').is_accessible_ex())

        print('testing Account port update ...')
        obj = models.Account.objects.first()
        obj.username = str(int(obj.username) + 1)
        obj.save()
        self.assertTrue(obj.nodes_ref.get(node__name='localhost').is_accessible_ex())

        print('testing Account notify() ...')
        for obj in models.Account.objects.all():
            self.assertTrue(obj.notify(sender=obj))

        print('testing Account toggle_active() ...')
        # all nas are active before test
        for na in models.NodeAccount.objects.all():
            self.assertTrue(na.is_active)

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

    def test_notify_validation(self):
        print('testing Account notify() validation ...')
        obj = models.Account.objects.first()
        obj.email = None
        self.assertRaisesRegex(ValidationError, 'email', obj.notify, sender=obj)

        obj = models.Account.objects.first()
        obj.is_active = False
        self.assertRaisesRegex(ValidationError, 'is_active', obj.notify, sender=obj)

        obj = models.Account.objects.first()
        # make all nodes inactive
        for node in models.Node.objects.all():
            node.is_active = False
            node.save()
        self.assertRaisesRegex(ValidationError, 'no active node', obj.notify, sender=obj)

    def test_notify_without_node_public_ip(self):
        print('testing Account notify() without node public IP address ...')
        for node in models.Node.objects.all():
            node.public_ip = None
            node.save()

        for obj in models.Account.objects.all():
            self.assertTrue(obj.notify(sender=obj))

    def test_notify_without_node_record(self):
        print('testing Account notify() without node record ...')
        for node in models.Node.objects.all():
            node.record = None
            node.save()

        for obj in models.Account.objects.all():
            self.assertTrue(obj.notify(sender=obj))

    def test_serializer(self):
        print('testing Account serializer ...')
        obj = serializers.AccountSerializer()
        json.loads(json.dumps(obj.to_representation(models.Account.objects.first())))


class NodeTestCase(TestCase):
    fixtures = AllData.fixtures

    @classmethod
    def up(cls):
        print('Node: loading data ...')
        DomainTestCase.up()
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
        AllData.up()

    @classmethod
    def tearDownClass(cls):
        AllData.down()
        super(NodeTestCase, cls).tearDownClass()

    def test_is_matching_record(self):
        print('testing Node is_matching_record() ...')
        for obj in models.Node.objects.all():
            if obj.record:
                self.assertTrue(obj.is_matching_record)
            else:
                self.assertFalse(obj.is_matching_record)

    def test_is_matching_dns_query(self):
        print('testing Node is_matching_dns_query() ...')
        for obj in models.Node.objects.all():
            self.assertFalse(obj.is_matching_dns_query)

    def test_clean(self):
        print('testing Node clean() ...')
        obj = models.Node.objects.first()
        obj.record = None
        obj.public_ip = None
        self.assertRaises(ValidationError, obj.clean)

        obj = models.Node.objects.filter(record__isnull=False, public_ip__isnull=False).first()
        obj.record = None
        obj.clean()

        obj = models.Node.objects.filter(record__isnull=False, public_ip__isnull=False).first()
        obj.public_ip = None
        obj.clean()

    def test_change_ips(self):
        print('testing Node change_ips() ...')
        # can't find a secure way to store credential for test
        self.assertRaisesRegex(ClientError, 'InvalidClientTokenId', models.Node.change_ips)

        obj = models.Node.objects.first()
        obj.sns_endpoint = None
        self.assertRaisesRegex(ValidationError, 'endpoint', obj.change_ip)

        obj = models.Node.objects.first()
        obj.sns_endpoint = 'an-invalid-arn'
        self.assertRaisesRegex(ValidationError, 'endpoint', obj.change_ip)

    def test_toggle_active(self):
        print('testing Node toggle_active() ...')
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

    def test_record_sync(self):
        print('testing Node record sync ...')
        # ip addresses are synced between node and record
        for obj in models.Node.objects.filter(record__isnull=False):
            self.assertTrue(obj.is_matching_record)

        # change nodes's public_ip
        for obj in models.Node.objects.filter(record__isnull=False):
            obj.public_ip = '.'.join(str(int(part)+3) for part in obj.public_ip.split('.'))
            obj.save()

        # ip addresses are synced between node and record
        for obj in models.Node.objects.filter(record__isnull=False):
            self.assertTrue(obj.is_matching_record)

        # make nodes inactive
        for obj in models.Node.objects.filter(record__isnull=False):
            obj.toggle_active()
            self.assertFalse(obj.is_active)

        # ip addresses are synced between node and record
        for obj in models.Node.objects.filter(record__isnull=False):
            self.assertTrue(obj.is_matching_record)

        # make nodes active
        for obj in models.Node.objects.filter(record__isnull=False):
            obj.toggle_active()
            self.assertTrue(obj.is_active)

        # ip addresses are synced between node and record
        for obj in models.Node.objects.filter(record__isnull=False):
            self.assertTrue(obj.is_matching_record)

    def test_serializer(self):
        print('testing Node serializer ...')
        obj = serializers.NodeSerializer()
        json.loads(json.dumps(obj.to_representation(models.Node.objects.first())))


class NodeAccountTestCase(TestCase):
    fixtures = AllData.fixtures

    @classmethod
    def up(cls):
        print('NodeAccount: loading data ...')
        # add all nodes to all accounts
        for account in models.Account.objects.all():
            account.add_all_nodes()

    def setUp(self):
        AllData.up()

    def tearDown(self):
        AllData.down()
        super(NodeAccountTestCase, self).tearDown()

    def test(self):
        print('testing NodeAccount heartbeat() ...')
        # perform the heartbeat once
        models.NodeAccount.heartbeat()

        # ssmanager is listening on localhost
        for obj in models.NodeAccount.objects.filter(node__ssmanagers__interface=models.InterfaceList.LOCALHOST):
            self.assertFalse(obj.is_created())
            self.assertTrue(obj.is_accessible_ex())
            obj.delete()

        # ssmanager is not listening on localhost
        for obj in models.NodeAccount.objects.exclude(node__ssmanagers__interface=models.InterfaceList.LOCALHOST):
            self.assertFalse(obj.is_created())
            self.assertFalse(obj.is_accessible_ex())
            obj.delete()

    def test_serializer(self):
        print('testing NodeAccount serializer ...')
        obj = serializers.NodeAccountSerializer()
        json.loads(json.dumps(obj.to_representation(models.NodeAccount.objects.first())))


class SSManagerTestCase(TestCase):
    fixtures = AllData.fixtures

    @classmethod
    def up(cls):
        print('SSManager: loading data ...')
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
    def down(cls):
        print('SSManager: tearing down ...')
        obj = models.SSManager.objects.filter(interface=models.InterfaceList.LOCALHOST).first()
        # explicitly delete the manager, so the server with a listening port is gone too.
        if obj: obj.delete()

    @classmethod
    def setUpTestData(cls):
        AllData.up()

    @classmethod
    def tearDownClass(cls):
        AllData.down()
        super(SSManagerTestCase, cls).tearDownClass()

    def test(self):
        print('testing SSManager ...')
        port=8388
        obj = models.SSManager.objects.filter(interface=models.InterfaceList.LOCALHOST).first()

        print('testing SSManager status ...')
        self.assertTrue(obj.is_accessible)
        self.assertTrue(obj.is_server_enabled)
        self.assertTrue(obj.server.version)
        self.assertRegexpMatches(obj.server.status, '(running|sleeping)')

        print('testing SSManager add() ...')
        obj.add(port, 'mock-password')
        self.assertFalse(obj.is_port_created(port))
        self.assertTrue(obj.is_port_created_or_accessible(port))

        print('testing SSManager remove() ...')
        obj.remove(port)
        self.assertFalse(obj.is_port_created(port))
        self.assertFalse(obj.is_port_created_or_accessible(port))

    def test_clean(self):
        print('testing SSManager clean() ...')
        obj = models.SSManager.objects.filter(interface=models.InterfaceList.PUBLIC).first()
        obj.node.public_ip = None
        self.assertRaises(ValidationError, obj.clean)

    def test_serializer(self):
        print('testing SSManager serializer ...')
        obj = serializers.SSManagerSerializer()
        json.loads(json.dumps(obj.to_representation(models.SSManager.objects.first())))
