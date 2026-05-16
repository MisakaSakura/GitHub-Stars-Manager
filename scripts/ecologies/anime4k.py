#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Anime4K ecology rules"""

from . import register_ecology

register_ecology('Anime4K', {'name_patterns': ['anime4k'], 'desc_patterns': ['anime4k', 'anime upscaler', 'real time upscaler'], 'topic_patterns': ['anime4k', 'anime-upscaling'], 'related_types': ['shader', 'filter', 'upscaler'], 'core_projects': ['anime4k']})
