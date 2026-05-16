#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Czkawka ecology rules"""

from . import register_ecology

register_ecology('Czkawka', {'name_patterns': ['czkawka'], 'desc_patterns': ['czkawka', 'find duplicates', 'similar images'], 'topic_patterns': ['czkawka', 'duplicates'], 'related_types': ['tool', 'cleaner'], 'core_projects': ['czkawka']})
