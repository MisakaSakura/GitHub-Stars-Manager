#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Starship ecology rules"""

from . import register_ecology

register_ecology('Starship', {'name_patterns': ['starship'], 'desc_patterns': ['starship', 'shell prompt'], 'topic_patterns': ['starship'], 'related_types': ['preset', 'config', 'theme'], 'core_projects': ['starship']})
