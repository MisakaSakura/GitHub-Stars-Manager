#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AwesomeWM ecology rules"""

from . import register_ecology

register_ecology('AwesomeWM', {'name_patterns': ['awesomewm', 'awesome-wm'], 'desc_patterns': ['awesome window manager', 'awesomewm'], 'topic_patterns': ['awesome-wm'], 'related_types': ['config', 'theme', 'widget'], 'core_projects': ['awesome']})
