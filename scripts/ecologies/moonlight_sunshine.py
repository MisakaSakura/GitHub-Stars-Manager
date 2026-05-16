#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Moonlight / Sunshine ecology rules"""

from . import register_ecology

register_ecology('Moonlight / Sunshine', {'name_patterns': ['moonlight', 'sunshine', 'apollo'], 'desc_patterns': ['moonlight', 'sunshine stream', 'game stream', 'nvidia gamestream', 'gamestream'], 'topic_patterns': ['moonlight', 'sunshine', 'game-streaming'], 'related_types': ['client', 'server', 'stream'], 'core_projects': ['moonlight', 'sunshine']})
