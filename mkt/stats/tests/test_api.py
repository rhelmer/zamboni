import json

import mock
from nose.tools import eq_, ok_
from rest_framework.reverse import reverse

from django.conf import settings

import amo

from mkt.api.tests.test_oauth import RestOAuth
from mkt.site.fixtures import fixture
from mkt.stats.api import APP_STATS, STATS


@mock.patch('monolith.client.Client')
@mock.patch.object(settings, 'MONOLITH_SERVER', 'http://0.0.0.0:0')
class TestGlobalStatsResource(RestOAuth):

    def setUp(self):
        super(TestGlobalStatsResource, self).setUp()
        self.create_switch('stats-api')
        self.grant_permission(self.profile, 'Stats:View')
        self.data = {'start': '2013-04-01',
                     'end': '2013-04-15',
                     'interval': 'day'}

    def url(self, metric=None):
        metric = metric or STATS.keys()[0]
        return reverse('global_stats', kwargs={'metric': metric})

    def test_cors(self, mocked):
        res = self.client.get(self.url(), data=self.data)
        self.assertCORS(res, 'get')

    def test_verbs(self, mocked):
        self._allowed_verbs(self.url(), ['get'])

    def test_anon(self, mocked):
        res = self.anon.get(self.url())
        eq_(res.status_code, 403)

    def test_bad_metric(self, mocked):
        res = self.client.get(self.url('foo'))
        eq_(res.status_code, 404)

    def test_missing_args(self, mocked):
        res = self.client.get(self.url())
        eq_(res.status_code, 400)
        data = json.loads(res.content)
        for f in ('start', 'end', 'interval'):
            eq_(data['detail'][f], ['This field is required.'])

    def test_good(self, mocked):
        res = self.client.get(self.url(), data=self.data)
        eq_(res.status_code, 200)
        eq_(json.loads(res.content)['objects'], [])

    def test_dimensions(self, mocked):
        client = mock.MagicMock()
        mocked.return_value = client

        data = self.data.copy()
        data.update({'region': 'br', 'package_type': 'hosted'})
        res = self.client.get(self.url('apps_added_by_package'), data=data)
        eq_(res.status_code, 200)
        ok_(client.called)
        eq_(client.call_args[1], {'region': 'br', 'package_type': 'hosted'})

    def test_dimensions_default(self, mocked):
        client = mock.MagicMock()
        mocked.return_value = client

        res = self.client.get(self.url('apps_added_by_package'),
                              data=self.data)
        eq_(res.status_code, 200)
        ok_(client.called)
        eq_(client.call_args[1], {'region': 'us', 'package_type': 'hosted'})

    def test_dimensions_default_is_none(self, mocked):
        client = mock.MagicMock()
        mocked.return_value = client

        res = self.client.get(self.url('apps_installed'), data=self.data)
        eq_(res.status_code, 200)
        ok_(client.called)
        eq_(client.call_args[1], {})

        data = self.data.copy()
        data['region'] = 'us'

        res = self.client.get(self.url('apps_installed'), data=data)
        eq_(res.status_code, 200)
        ok_(client.called)
        eq_(client.call_args[1], {'region': 'us'})


@mock.patch('monolith.client.Client')
@mock.patch.object(settings, 'MONOLITH_SERVER', 'http://0.0.0.0:0')
class TestAppStatsResource(RestOAuth):
    fixtures = fixture('user_2519')

    def setUp(self):
        super(TestAppStatsResource, self).setUp()
        self.create_switch('stats-api')
        self.app = amo.tests.app_factory(status=amo.STATUS_PUBLIC)
        self.app.addonuser_set.create(user=self.user.get_profile())
        self.data = {'start': '2013-04-01', 'end': '2013-04-15',
                     'interval': 'day'}

    def url(self, pk=None, metric=None):
        pk = pk or self.app.pk
        metric = metric or APP_STATS.keys()[0]
        return reverse('app_stats', kwargs={'pk': pk, 'metric': metric})

    def test_cors(self, mocked):
        res = self.client.get(self.url(), data=self.data)
        self.assertCORS(res, 'get')

    def test_verbs(self, mocked):
        self._allowed_verbs(self.url(), ['get'])

    def test_anon(self, mocked):
        res = self.anon.get(self.url())
        eq_(res.status_code, 403)

    def test_bad_app(self, mocked):
        res = self.client.get(self.url(pk=99999999))
        eq_(res.status_code, 404)

    def test_bad_metric(self, mocked):
        res = self.client.get(self.url(metric='foo'))
        eq_(res.status_code, 404)

    def test_missing_args(self, mocked):
        res = self.client.get(self.url())
        eq_(res.status_code, 400)
        data = json.loads(res.content)
        for f in ('start', 'end', 'interval'):
            eq_(data['detail'][f], ['This field is required.'])
