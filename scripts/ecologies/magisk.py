#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Magisk ecology rules"""

from . import register_ecology

register_ecology('Magisk', {'name_patterns': ['magisk'], 'desc_patterns': ['magisk', 'magisk module', 'root solution'], 'topic_patterns': ['magisk', 'magisk-module'], 'related_types': ['module', 'manager'], 'core_projects': ['magisk']})
