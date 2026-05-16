#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OBS Studio ecology rules"""

from . import register_ecology

register_ecology('OBS Studio', {'name_patterns': ['obs', 'obs-studio', 'streamfx', 'input-overlay'], 'desc_patterns': ['obs plugin', 'obs studio', 'obs-studio'], 'topic_patterns': ['obs', 'obs-studio'], 'related_types': ['plugin', 'script', 'theme'], 'core_projects': ['obs-studio']})
