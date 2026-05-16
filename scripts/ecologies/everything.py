#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Everything ecology rules"""

from . import register_ecology

register_ecology('Everything', {'name_patterns': ['everything'], 'desc_patterns': ['everything search', 'file search'], 'topic_patterns': ['everything'], 'related_types': ['search', 'toolbar'], 'core_projects': ['everything']})
