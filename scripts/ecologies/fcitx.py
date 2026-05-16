#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fcitx ecology rules"""

from . import register_ecology

register_ecology('fcitx', {'name_patterns': ['fcitx'], 'desc_patterns': ['fcitx', 'input method'], 'topic_patterns': ['fcitx', 'fcitx5'], 'related_types': ['ime', 'keyboard', 'engine'], 'core_projects': ['fcitx']})
