#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Typora ecology rules"""

from . import register_ecology

register_ecology('Typora', {'name_patterns': ['typora'], 'desc_patterns': ['typora theme', 'typora plugin'], 'topic_patterns': ['typora'], 'related_types': ['theme', 'plugin'], 'core_projects': ['typora']})
