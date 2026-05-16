#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RSS / 阅读 ecology rules"""

from . import register_ecology

register_ecology('RSS / 阅读', {'name_patterns': ['rsshub', 'folo', 'koodo-reader', 'readest'], 'desc_patterns': ['rss reader', 'rss hub', 'ebook reader', 'ebook manager'], 'topic_patterns': ['rss', 'rss-reader', 'ebook', 'ebook-reader'], 'related_types': ['reader', 'client', 'server'], 'core_projects': ['rsshub', 'folo']})
