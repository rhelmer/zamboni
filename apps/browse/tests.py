# -*- coding: utf-8 -*-
from django import http
from django.core.cache import cache
from django.utils import http as urllib

import mock
from nose.tools import eq_, assert_raises
from pyquery import PyQuery as pq

import test_utils

import amo
import amo.test_utils
from amo.urlresolvers import reverse
from amo.helpers import urlparams
from addons.models import Addon, Category
from addons.cron import _update_appsupport
from browse import views, feeds
from browse.views import locale_display_name
from translations.models import Translation
from translations.query import order_by_translation
from versions.models import Version


def test_locale_display_name():

    def check(locale, english, native):
        actual = locale_display_name(locale)
        eq_(actual, (english, native))

    check('el', 'Greek', u'Ελληνικά')
    check('el-XX', 'Greek', u'Ελληνικά')
    assert_raises(KeyError, check, 'fake-lang', '', '')


class TestLanguageTools(amo.test_utils.ExtraSetup, test_utils.TestCase):
    fixtures = ['browse/test_views']

    def setUp(self):
        super(TestLanguageTools, self).setUp()
        cache.clear()
        self.url = reverse('browse.language-tools')
        response = self.client.get(self.url, follow=True)
        # For some reason the context doesn't get loaded the first time.
        response = self.client.get(self.url, follow=True)
        self.locales = list(response.context['locales'])

    def test_sorting(self):
        """The locales should be sorted by English display name."""
        displays = [locale.display for _, locale in self.locales]
        eq_(displays, sorted(displays))

    def test_native_missing_region(self):
        """
        If we had to strip a locale's region to find a display name, we
        append it to the native name for disambiguation.
        """
        el = dict(self.locales)['el-XX']
        assert el.native.endswith(' (el-xx)')

    def test_missing_locale(self):
        """If we don't know about a locale, show the addon name and locale."""
        wa = dict(self.locales)['wa']
        eq_(wa.display, 'Walloon Language Pack (wa)')
        eq_(wa.native, '')

    def test_packs_and_dicts(self):
        ca = dict(self.locales)['ca-valencia']
        eq_(len(ca.dicts), 1)
        eq_(len(ca.packs), 3)

    def test_empty_target_locale(self):
        """Make sure nothing breaks with empty target locales."""
        for addon in Addon.objects.all():
            addon.target_locale = ''
            addon.save()
        response = self.client.get(self.url, follow=True)
        eq_(response.status_code, 200)
        eq_(list(response.context['locales']), [])

    def test_null_target_locale(self):
        """Make sure nothing breaks with null target locales."""
        for addon in Addon.objects.all():
            addon.target_locale = None
            addon.save()
        response = self.client.get(self.url, follow=True)
        eq_(response.status_code, 200)
        eq_(list(response.context['locales']), [])


class TestThemes(amo.test_utils.ExtraSetup, test_utils.TestCase):
    fixtures = ('base/category', 'base/addon_6704_grapple', 'base/addon_3615')

    def setUp(self):
        super(TestThemes, self).setUp()
        # Make all the add-ons themes.
        for addon in Addon.objects.all():
            addon.type = amo.ADDON_THEME
            addon.save()
        for category in Category.objects.all():
            category.type = amo.ADDON_THEME
            category.save()

        self.base_url = reverse('browse.themes')
        self.exp_url = urlparams(self.base_url, unreviewed=True)

    def test_default_sort(self):
        """Default sort should be by popular."""
        response = self.client.get(self.base_url)
        eq_(response.context['sorting'], 'popular')

    def test_unreviewed(self):
        # Only 3 without unreviewed.
        response = self.client.get(self.base_url)
        eq_(len(response.context['themes'].object_list), 2)

        response = self.client.get(self.exp_url)
        eq_(len(response.context['themes'].object_list), 2)

    def _get_sort(self, sort):
        response = self.client.get(urlparams(self.exp_url, sort=sort))
        eq_(response.context['sorting'], sort)
        return [a.id for a in response.context['themes'].object_list]

    def test_download_sort(self):
        ids = self._get_sort('popular')
        eq_(ids, [3615, 6704])

    def test_name_sort(self):
        ids = self._get_sort('name')
        eq_(ids, [3615, 6704])

    def test_created_sort(self):
        ids = self._get_sort('created')
        eq_(ids, [6704, 3615])

    def test_updated_sort(self):
        ids = self._get_sort('updated')
        eq_(ids, [6704, 3615])

    def test_rating_sort(self):
        ids = self._get_sort('rating')
        eq_(ids, [6704, 3615])

    def test_category_count(self):
        cat = Category.objects.filter(name__isnull=False)[0]
        response = self.client.get(reverse('browse.themes', args=[cat.slug]))
        doc = pq(response.content)
        actual_count = int(doc('hgroup h3').text().split()[0])
        page = response.context['themes']
        expected_count = page.paginator.count
        eq_(actual_count, expected_count)


class TestCategoryPages(amo.test_utils.ExtraSetup, test_utils.TestCase):
    fixtures = ('base/apps', 'base/category', 'base/addon_3615',
                'base/featured', 'addons/featured', 'browse/nameless-addon')

    def test_browsing_urls(self):
        """Every browse page URL exists."""
        for _, slug in amo.ADDON_SLUGS.items():
            assert reverse('browse.%s' % slug)

    def test_matching_opts(self):
        """Every filter on landing pages is available on listing pages."""
        for key, _ in views.CategoryLandingFilter.opts:
            if key != 'featured':
                assert key in dict(views.AddonFilter.opts)

    @mock.patch('browse.views.category_landing')
    def test_goto_category_landing(self, landing_mock):
        """We hit a landing page if there's a category and no sorting."""
        landing_mock.return_value = http.HttpResponse()

        self.client.get(reverse('browse.extensions'))
        assert not landing_mock.called

        slug = Category.objects.all()[0].slug
        category_url = reverse('browse.extensions', args=[slug])
        self.client.get('%s?sort=created' % category_url)
        assert not landing_mock.called

        self.client.get(category_url)
        assert landing_mock.called

    def test_creatured_addons(self):
        """Make sure the creatured add-ons are for the right category."""
        # Featured in bookmarks.
        url = reverse('browse.extensions', args=['bookmarks'])
        response = self.client.get(url, follow=True)
        creatured = response.context['filter'].all()['featured']
        eq_(len(creatured), 1)
        eq_(creatured[0].id, 3615)

        # Not featured in search-tools.
        url = reverse('browse.extensions', args=['search-tools'])
        response = self.client.get(url, follow=True)
        creatured = response.context['filter'].all()['featured']
        eq_(len(creatured), 0)

    def test_creatured_only_public(self):
        """Make sure the creatured add-ons are all public."""
        url = reverse('browse.creatured', args=['bookmarks'])
        r = self.client.get(url, follow=True)
        addons = r.context['addons']

        for a in addons:
            assert a.status == amo.STATUS_PUBLIC, "%s is not public" % a.name

        old_count = len(addons)
        addons[0].status = amo.STATUS_UNREVIEWED
        addons[0].save()
        r = self.client.get(url, follow=True)
        addons = r.context['addons']

        for a in addons:
            assert a.status == amo.STATUS_PUBLIC, ("Altered %s is featured"
                                                   % a.name)

        eq_(len(addons), old_count - 1, "The number of addons is the same.")

    def test_added_date(self):
        url = reverse('browse.extensions') + '?sort=created'
        doc = pq(self.client.get(url).content)
        s = doc('.featured .item .updated').text()
        assert s.strip().startswith('Added'), s

    def test_sorting_nameless(self):
        """Nameless add-ons are dropped from the sort."""
        qs = Addon.objects.all()
        ids = order_by_translation(qs, 'name')
        assert 57132 in [a.id for a in qs]
        assert 57132 not in [a.id for a in ids]


class TestLegacyRedirects(test_utils.TestCase):
    fixtures = ('base/category.json',)

    def test_types(self):
        def redirects(from_, to):
            r = self.client.get('/en-US/firefox' + from_)
            self.assertRedirects(r, '/en-US/firefox' + to, status_code=301,
                                 msg_prefix="Redirection failed: %s" % to)

        redirects('/browse/type:1', '/extensions/')
        redirects('/browse/type:1/', '/extensions/')
        redirects('/browse/type:1/cat:all', '/extensions/')
        redirects('/browse/type:1/cat:all/', '/extensions/')
        redirects('/browse/type:1/cat:72', '/extensions/alerts-updates/')
        redirects('/browse/type:1/cat:72/', '/extensions/alerts-updates/')

        redirects('/browse/type:2', '/themes/')
        redirects('/browse/type:3', '/language-tools/')
        redirects('/browse/type:4', '/search-tools/')
        redirects('/search-engines', '/search-tools/')
        # redirects('/browse/type:7', '/plugins/')
        redirects('/recommended', '/featured')
        redirects('/recommended/format:rss', '/featured/format:rss')

class TestFeaturedPage(amo.test_utils.ExtraSetup, test_utils.TestCase):
    fixtures = ('base/apps', 'addons/featured')

    def test_featured_addons(self):
        """Make sure that only featured add-ons are shown"""

        response = self.client.get(reverse('browse.featured'))
        eq_([1001,1003], [a.id for a in response.context['addons']])

class TestCategoriesFeed(test_utils.TestCase):

    def setUp(self):
        self.feed = feeds.CategoriesRss()
        self.u = u'Ελληνικά'
        self.wut = Translation(localized_string=self.u, locale='el')

        self.feed.request = mock.Mock()
        self.feed.request.APP.pretty = self.u

        self.category = Category(name=self.u)

        self.addon = Addon(name=self.u, id=2)
        self.addon._current_version = Version(version='v%s' % self.u)

    def test_title(self):
        eq_(self.feed.title(self.category),
            u'%s :: Add-ons for %s' % (self.wut, self.u))

    def test_item_title(self):
        eq_(self.feed.item_title(self.addon),
            u'%s v%s' % (self.u, self.u))

    def test_item_guid(self):
        t = self.feed.item_guid(self.addon)
        assert t.endswith(u'/addon/2/versions/v%s' % urllib.urlquote(self.u))

class TestFeaturedFeed(amo.test_utils.ExtraSetup, test_utils.TestCase):
    fixtures = ('base/apps', 'addons/featured')

    def test_feed_elements_present(self):
        """specific elements are present and reasonably well formed"""
        url = reverse('browse.featured.rss')
        r = self.client.get(url, follow=True)
        doc = pq(r.content)
        eq_(doc('rss channel title')[0].text,
                'Featured Add-ons :: Add-ons for Firefox')
        assert doc('rss channel link')[0].text.endswith('/en-US/firefox/')
        eq_(doc('rss channel description')[0].text,
                "Here's a few of our favorite add-ons to help you get " \
                "started customizing Firefox.")
        assert len(doc('rss channel item title')[0].text) > 0
        item_link = doc('rss channel item link')[0]
        assert item_link.text.endswith('/addon/1003/') \
               or item_link.text.endswith('/addon/1001/')
        item_pubdate = doc('rss channel item pubDate')[0]
        assert item_pubdate.text == 'Tue, 17 Jan 2006 07:28:30 -0800' \
               or item_pubdate.text == 'Tue, 02 Jan 2007 16:57:55 -0800'
        item_guid = doc('rss channel item guid')[0]
        assert item_guid.text.endswith('/versions/1.0.42') or \
               item_guid.text.endswith('/versions/1.0.43')
