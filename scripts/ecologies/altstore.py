#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AltStore ecology rules"""

from . import register_ecology

register_ecology('AltStore', {'name_patterns': ['altstore'], 'desc_patterns': ['altstore', 'alternative app store', 'sideload'], 'topic_patterns': ['altstore'], 'related_types': ['app', 'installer'], 'core_projects': ['altstore']})
