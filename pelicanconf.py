#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = u'X-Chu'
SITENAME = u'EdgeDef: Do Things You Cannot Do'
SITEURL = 'http://edgedef.com'


GITHUB_URL = "http://github.com/xychu/xychu_pelican"

#THEME = 'pelican-bootstrap3'
THEME = 'zurb-F5-basic'
OUTPUT_PATH = '../xychu.github.io/'
PATH = 'content'

STATIC_PATHS = ['images', 'extra/CNAME']
EXTRA_PATH_METADATA = {'extra/CNAME': {'path': 'CNAME'},}

TIMEZONE = 'Asia/Shanghai'

DEFAULT_LANG = u'zh'
import datetime
td = datetime.date.today()
DEFAULT_DATE = (td.year, td.month, td.day, 0, 0, 0)
#LOCALE = ("zh_CN")
#DATE_FORMAT = {
#        'zh': ('zh_CN', '%Y-%m-%d, %a'),
#        }

PLUGIN_PATH = ['pelican-plugins']
PLUGINS = ['sitemap']

SITEMAP = {
        'format': 'xml',
        'priorities': {
            'articles': 0.7,
            'indexes': 0.5,
            'pages': 0.3
         },
         'changefreqs': {
             'articles': 'monthly',
             'indexes': 'daily',
             'pages': 'monthly'
         }
}


# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None

# Blogroll
LINKS = (
    (u'豆瓣读书主页', 'http://book.douban.com/people/58301079/'),
)
# Social widget
SOCIAL = (
    ('GitHub', 'https://github.com/xychu'),
    ('Weibo', 'http://weibo.com/learn2live'),
)

DEFAULT_PAGINATION = 10

# Uncomment following line if you want document-relative URLs when developing
RELATIVE_URLS = True

