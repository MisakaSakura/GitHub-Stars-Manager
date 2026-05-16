#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bilibili ecology rules"""

from . import register_ecology

register_ecology('Bilibili', {'name_patterns': ['bilibili', 'bbll', 'downkyi', 'bilitools', 'bili-copilot'], 'desc_patterns': ['bilibili', '哔哩', 'third-party bilibili'], 'topic_patterns': ['bilibili'], 'related_types': ['client', 'downloader', 'tool', 'plugin'], 'core_projects': ['bilibili']})
