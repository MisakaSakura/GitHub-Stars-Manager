#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mihon / Tachiyomi ecology rules"""

from . import register_ecology

register_ecology('Mihon / Tachiyomi', {'name_patterns': ['mihon', 'tachiyomi'], 'desc_patterns': ['mihon', 'tachiyomi', 'manga reader'], 'topic_patterns': ['mihon', 'tachiyomi', 'manga'], 'related_types': ['extension', 'source', 'reader'], 'core_projects': ['mihon', 'tachiyomi']})
