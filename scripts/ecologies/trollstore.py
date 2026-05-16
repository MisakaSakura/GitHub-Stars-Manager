#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TrollStore ecology rules"""

from . import register_ecology

register_ecology('TrollStore', {'name_patterns': ['trollstore'], 'desc_patterns': ['trollstore', 'ios app installer', 'jailed ios'], 'topic_patterns': ['trollstore'], 'related_types': ['tool', 'installer'], 'core_projects': ['trollstore']})
