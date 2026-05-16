#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""neofetch / fastfetch ecology rules"""

from . import register_ecology

register_ecology('neofetch / fastfetch', {'name_patterns': ['neofetch', 'fastfetch'], 'desc_patterns': ['neofetch', 'fastfetch', 'system information'], 'topic_patterns': ['neofetch', 'fastfetch'], 'related_types': ['theme', 'config'], 'core_projects': ['neofetch', 'fastfetch']})
