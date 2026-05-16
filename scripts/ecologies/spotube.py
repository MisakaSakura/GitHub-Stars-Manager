#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Spotube ecology rules"""

from . import register_ecology

register_ecology('Spotube', {'name_patterns': ['spotube'], 'desc_patterns': ['spotube', 'spotify client'], 'topic_patterns': ['spotube', 'spotify'], 'related_types': ['client', 'player'], 'core_projects': ['spotube']})
