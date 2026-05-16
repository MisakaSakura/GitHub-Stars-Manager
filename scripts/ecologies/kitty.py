#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kitty ecology rules"""

from . import register_ecology

register_ecology('Kitty', {'name_patterns': ['kitty'], 'desc_patterns': ['kitty terminal', 'kitty config'], 'topic_patterns': ['kitty'], 'related_types': ['theme', 'config', 'script'], 'core_projects': ['kitty']})
