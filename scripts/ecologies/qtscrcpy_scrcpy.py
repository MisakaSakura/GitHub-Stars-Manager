#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QtScrcpy / Scrcpy ecology rules"""

from . import register_ecology

register_ecology('QtScrcpy / Scrcpy', {'name_patterns': ['scrcpy', 'qtscrcpy'], 'desc_patterns': ['scrcpy', 'qtscrcpy', 'mirror your android'], 'topic_patterns': ['scrcpy'], 'related_types': ['tool', 'gui'], 'core_projects': ['scrcpy']})
