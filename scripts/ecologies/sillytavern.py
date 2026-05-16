#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SillyTavern ecology rules"""

from . import register_ecology

register_ecology('SillyTavern', {'name_patterns': ['sillytavern'], 'desc_patterns': ['sillytavern', 'llm frontend', 'ai roleplay'], 'topic_patterns': ['sillytavern'], 'related_types': ['extension', 'theme', 'script'], 'core_projects': ['sillytavern']})
