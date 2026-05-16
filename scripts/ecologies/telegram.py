#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Telegram ecology rules"""

from . import register_ecology

register_ecology('Telegram', {'name_patterns': ['telegram', 'tdesktop', 'ayugram'], 'desc_patterns': ['telegram client', 'telegram desktop', 'telegram app'], 'topic_patterns': ['telegram', 'telegram-client'], 'related_types': ['client', 'mod', 'theme'], 'core_projects': ['telegram']})
