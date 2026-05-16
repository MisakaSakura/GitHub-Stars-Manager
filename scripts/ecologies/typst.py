#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Typst ecology rules"""

from . import register_ecology

register_ecology('Typst', {'name_patterns': ['typst'], 'desc_patterns': ['typst', 'typesetting system'], 'topic_patterns': ['typst'], 'related_types': ['compiler', 'editor', 'template'], 'core_projects': ['typst']})
