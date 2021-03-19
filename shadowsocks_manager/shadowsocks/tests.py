# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.models import Max
from botocore.exceptions import ClientError

from domain.models import Record
from domain.tests import TestData as DomainTestData
from notification.tests import TestData as NotificationTestData
from . import models


# Create your tests here.
class TestData:
    fixtures = ['config.json', 'auth.group.json']
    fixtures.extend(DomainTestData.fixtures)
    fixtures.extend(NotificationTestData.fixtures)

    @classmethod
    def all(cls):
        cls.config()
        cls.account()
        cls.node()
        cls.ssmanager()
        cls.nodeaccount()

    @classmethod
    def config(cls):
        obj = models.Config.load()
        obj.timeout=0.1  # minimal the waiting time
        obj.save()

    @classmethod
    def account(cls):
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
    def node(cls):
        DomainTestData.all()
        record = Record.objects.first()

        # generate 3 nodes
        for i in list(range(1, 4)):
            obj = models.Node(
                name='mock-node-{}'.format(i),
                record=record,
                public_ip='.'.join([str(i) for j in list(range(4))]),
                private_ip='172.0.0.1',
                location='mock-locaction-{}'.format(i),
                sns_endpoint='arn:aws:sns:ap-northeast-1:{}:topic'.format(i),
                sns_access_key='mock-sns_access_key-{}'.format(i),
                sns_secret_key='mock-sns_secret_key-{}'.format(i),
                is_active=True,
            )
            obj.save()

    @classmethod
    def ssmanager(cls):
        for node in models.Node.objects.all():
            interface = node.pk % 4  # valid interface list: 1,2,3
            if interface == 0: interface = 1
            obj = models.SSManager(
                node=node,
                interface=interface
            )
            obj.save()

    @classmethod
    def nodeaccount(cls):
        for account in models.Account.objects.all():
            account.add_all_nodes()


class ConfigTestCase(TestCase):
    fixtures = TestData.fixtures

    def setUp(self):
        TestData.config()

    def test(self):
        self.assertEqual(models.Config.load(), models.Config.objects.first())


class AccountTestCase(TestCase):
    fixtures = TestData.fixtures

    @classmethod
    def setUpTestData(cls):
        TestData.all()

    def test_clean(self):
        obj = models.Account.objects.first()
        obj.username = str(int(obj.username) - 1)
        self.assertRaises(ValidationError, obj.clean)

        obj = models.Account.objects.last()
        obj.username = str(int(obj.username) + 1)
        self.assertRaises(ValidationError, obj.clean)

    def test_notify_validation(self):
        obj = models.Account.objects.first()
        obj.email = None
        self.assertRaisesRegex(ValidationError, 'email', obj.notify, sender=obj)

        obj = models.Account.objects.first()
        obj.is_active = False
        self.assertRaisesRegex(ValidationError, 'is_active', obj.notify, sender=obj)

        obj = models.Account.objects.first()
        for node in models.Node.objects.all():
            node.toggle_active()
        self.assertRaisesRegex(ValidationError, 'no active node', obj.notify, sender=obj)

    def test_notify_without_node_public_ip(self):
        for node in models.Node.objects.all():
            node.public_ip = None
            node.save()

        for obj in models.Account.objects.all():
            self.assertTrue(obj.notify(sender=obj))

        # restore the data since using setUpTestData()
        for node in models.Node.objects.all():
            node.public_ip = '.'.join([str(node.pk) for j in list(range(4))])
            node.save()

    def test_notify_without_node_record(self):
        for node in models.Node.objects.all():
            node.record = None
            node.save()

        for obj in models.Account.objects.all():
            self.assertTrue(obj.notify(sender=obj))

        # restore the data since using setUpTestData()
        for node in models.Node.objects.all():
            node.record = Record.objects.first()
            node.save()

    def test_notify_with_domain(self):
        for obj in models.Account.objects.all():
            self.assertTrue(obj.notify(sender=obj))

    def test_toggle_active(self):
        # na is True before test
        for na in models.NodeAccount.objects.all():
            self.assertTrue(na.is_active)

        # make accounts inactive
        for obj in models.Account.objects.all():
            obj.toggle_active()
            self.assertFalse(obj.is_active)

        # na is False now
        for na in models.NodeAccount.objects.all():
            self.assertFalse(na.is_active)

        # make accounts active
        for obj in models.Account.objects.all():
            obj.toggle_active()
            self.assertTrue(obj.is_active)

        # na is True now
        for na in models.NodeAccount.objects.all():
            self.assertTrue(na.is_active)

    def test_update_username(self):
        for obj in models.Account.objects.all():
            obj = models.Account.objects.first()
            obj.username = str(int(obj.username) + 1)
            obj.save()

    def test_update_password(self):
        for obj in models.Account.objects.all():
            obj = models.Account.objects.first()
            obj.password = 'mock-new-password'
            obj.save()


class NodeTestCase(TestCase):
    fixtures = TestData.fixtures

    @classmethod
    def setUpTestData(cls):
        TestData.all()

    def test_with_record(self):
        obj = models.Node.objects.first()
        obj.on_update()
        self.assertTrue(obj.is_matching_record)
        self.assertFalse(obj.is_matching_dns_query)

    def test_without_record(self):
        obj = models.Node.objects.first()
        obj.record = None
        obj.on_update()
        self.assertFalse(obj.is_matching_record)
        self.assertFalse(obj.is_matching_dns_query)

    def test_clean(self):
        obj = models.Node.objects.first()
        obj.record = None
        obj.public_ip = None
        self.assertRaises(ValidationError, obj.clean)

        obj = models.Node.objects.first()
        obj.record = None
        obj.clean

        obj = models.Node.objects.first()
        obj.public_ip = None
        obj.clean

    def test_change_ips(self):
        self.assertRaises(ClientError, models.Node.change_ips)

        obj = models.Node.objects.first()
        obj.sns_endpoint = None
        self.assertRaises(ValidationError, obj.change_ip)

        obj = models.Node.objects.first()
        obj.sns_endpoint = 'an-invalid-arn'
        self.assertRaises(ValidationError, obj.change_ip)

    def test_toggle_active(self):
        # na is True before test
        for na in models.NodeAccount.objects.all():
            self.assertTrue(na.is_active)

        # make nodes inactive
        for obj in models.Node.objects.all():
            obj.toggle_active()
            self.assertFalse(obj.is_active)

        # na is False now
        for na in models.NodeAccount.objects.all():
            self.assertFalse(na.is_active)

        # make nodes active
        for obj in models.Node.objects.all():
            obj.toggle_active()
            self.assertTrue(obj.is_active)

        # na is True now
        for na in models.NodeAccount.objects.all():
            self.assertTrue(na.is_active)

    def test_record_update(self):
        # ips are synced between node and record
        for obj in models.Node.objects.all():
            self.assertTrue(obj.is_matching_record)

        # change nodes's public_ip
        for obj in models.Node.objects.all():
            obj.public_ip = '.'.join([str(int(part)+3) for part in obj.public_ip.split('.')])
            obj.save()

        # ips are synced between node and record
        for obj in models.Node.objects.all():
            self.assertTrue(obj.is_matching_record)

        # make nodes inactive
        for obj in models.Node.objects.all():
            obj.toggle_active()
            self.assertFalse(obj.is_active)

        # ips are synced between node and record
        for obj in models.Node.objects.all():
            self.assertTrue(obj.is_matching_record)

        # make nodes active
        for obj in models.Node.objects.all():
            obj.toggle_active()
            self.assertTrue(obj.is_active)

        # ips are synced between node and record
        for obj in models.Node.objects.all():
            self.assertTrue(obj.is_matching_record)


class NodeAccountTestCase(TestCase):
    fixtures = TestData.fixtures

    def setUp(self):
        TestData.all()

    def test(self):
        models.NodeAccount.heartbeat()

        for obj in models.NodeAccount.objects.all():
            self.assertFalse(obj.is_created())
            self.assertFalse(obj.is_accessible)
            obj.delete()


class SSManagerTestCase(TestCase):
    fixtures = TestData.fixtures

    def setUp(self):
        TestData.node()
        TestData.ssmanager()

    def test(self):
        obj = models.SSManager.objects.filter(interface=3).first()
        obj.node.public_ip = None
        self.assertRaises(ValidationError, obj.clean)

        obj = models.SSManager.objects.filter(interface=3).first()
        obj.clear_cache()
        obj.add('8000', 'mock-password')
        obj.remove('8000')
