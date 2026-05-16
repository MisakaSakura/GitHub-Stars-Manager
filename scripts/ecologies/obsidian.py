#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Obsidian ecology rules"""

from . import register_ecology

register_ecology('Obsidian', {'name_patterns': ['obsidian'], 'desc_patterns': ['obsidian plugin', 'obsidian theme'], 'topic_patterns': ['obsidian'], 'related_types': ['plugin', 'theme', 'snippet'], 'core_projects': ['obsidian']})
