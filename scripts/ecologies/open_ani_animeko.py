#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""open-ani / Animeko ecology rules"""

from . import register_ecology

register_ecology('open-ani / Animeko', {'name_patterns': ['animeko', 'open-ani'], 'desc_patterns': ['animeko', 'open-ani', 'bangumi', '弹幕追番'], 'topic_patterns': ['anime', 'bangumi'], 'related_types': ['client', 'player'], 'core_projects': ['animeko']})
