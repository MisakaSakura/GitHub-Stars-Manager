#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MPV ecology rules"""

from . import register_ecology

register_ecology('MPV', {'name_patterns': ['mpv'], 'desc_patterns': ['mpv', 'mpv player', 'lua script', 'mpv plugin'], 'topic_patterns': ['mpv'], 'related_types': ['script', 'config', 'gui', 'skin', 'theme', 'thumbnail'], 'core_projects': ['mpv']})
