#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""i3 / Sway ecology rules"""

from . import register_ecology

register_ecology('i3 / Sway', {'name_patterns': ['i3', 'sway', 'polybar', 'rofi', 'dunst'], 'desc_patterns': ['i3wm', 'swaywm', 'tiling window manager'], 'topic_patterns': ['i3', 'sway', 'window-manager'], 'related_types': ['config', 'theme', 'script', 'bar'], 'core_projects': ['i3', 'sway']})
