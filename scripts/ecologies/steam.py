#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Steam ecology rules"""

from . import register_ecology

register_ecology('Steam', {'name_patterns': ['steam', 'millennium'], 'desc_patterns': ['steam client', 'steam theme', 'steam plugin', 'steam mod'], 'topic_patterns': ['steam'], 'related_types': ['theme', 'plugin', 'mod', 'skin'], 'core_projects': ['steam']})
