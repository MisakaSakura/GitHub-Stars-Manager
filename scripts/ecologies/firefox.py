#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Firefox ecology rules"""

from . import register_ecology

register_ecology('Firefox', {'name_patterns': ['firefox', 'zen-browser'], 'desc_patterns': ['firefox', 'firefox-based', 'firefox browser'], 'topic_patterns': ['firefox', 'firefox-based'], 'related_types': ['browser', 'extension', 'theme'], 'core_projects': ['firefox']})
