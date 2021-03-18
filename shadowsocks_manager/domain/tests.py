# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals

from django.test import TestCase

from domain.models import NameServer, Domain, Record

class DomainTestCase(TestCase):
    fixtures = ['nameserver.json']

    def setUp(self):
        for ns in NameServer.objects.all():
            if not ns.user:
                ns.user = 'mockuser'
            if not ns.credential:
                ns.credential = 'mockcredential'
            ns.save()

            # generate domain
            d = Domain(name='example-{}.com'.format(ns.pk), nameserver=ns)
            d.save()

            # generate record
            r = Record(host='www', domain=d, type='A', answer='1.1.1.1')
            r.save()

    def test(self):
        for r in Record.objects.all():
            # nameserver
            self.assertTrue(str(r.domain.nameserver))
            self.assertFalse(r.domain.nameserver.is_api_accessible)

            # domain
            self.assertTrue(str(r.domain))

            # record
            self.assertTrue(str(r))
            self.assertFalse(r.is_matching_dns_query)
            r.delete()
