#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aria2 ecology rules"""

from . import register_ecology

register_ecology('Aria2', {'name_patterns': ['aria2', 'ariang'], 'desc_patterns': ['aria2', 'aria-ng', 'aria download'], 'topic_patterns': ['ariang'], 'related_types': ['web-ui', 'gui', 'client'], 'core_projects': ['aria2']})
