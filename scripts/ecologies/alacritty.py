#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Alacritty ecology rules"""

from . import register_ecology

register_ecology('Alacritty', {'name_patterns': ['alacritty'], 'desc_patterns': ['alacritty', 'terminal emulator'], 'topic_patterns': ['alacritty'], 'related_types': ['theme', 'config'], 'core_projects': ['alacritty']})
