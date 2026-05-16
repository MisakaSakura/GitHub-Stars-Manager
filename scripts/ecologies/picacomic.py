#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PicaComic ecology rules"""

from . import register_ecology

register_ecology('PicaComic', {'name_patterns': ['picacomic'], 'desc_patterns': ['picacomic', 'comic app'], 'topic_patterns': ['picacomic', 'comic'], 'related_types': ['client', 'reader'], 'core_projects': ['picacomic']})
