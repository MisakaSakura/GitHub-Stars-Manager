#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Electron ecology rules"""

from . import register_ecology

register_ecology('Electron', {'name_patterns': ['electron'], 'desc_patterns': ['electron app', 'electron-based', 'cross-platform desktop'], 'topic_patterns': [], 'related_types': ['app', 'tool', 'client'], 'core_projects': ['electron']})
