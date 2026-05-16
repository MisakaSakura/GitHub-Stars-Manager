#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WSL ecology rules"""

from . import register_ecology

register_ecology('WSL', {'name_patterns': ['wsl'], 'desc_patterns': ['windows subsystem for linux', 'wsl distribution'], 'topic_patterns': ['wsl'], 'related_types': ['distribution', 'tool'], 'core_projects': ['wsl']})
