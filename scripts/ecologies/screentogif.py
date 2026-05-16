#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ScreenToGif ecology rules"""

from . import register_ecology

register_ecology('ScreenToGif', {'name_patterns': ['screentogif'], 'desc_patterns': ['screentogif', 'screen to gif'], 'topic_patterns': ['screentogif', 'gif-recorder'], 'related_types': ['recorder', 'editor'], 'core_projects': ['screentogif']})
