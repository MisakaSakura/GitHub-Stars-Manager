#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scoop ecology rules"""

from . import register_ecology

register_ecology('Scoop', {'name_patterns': ['scoop'], 'desc_patterns': ['scoop bucket', 'scoop manifest', 'windows package manager'], 'topic_patterns': ['scoop'], 'related_types': ['bucket', 'manifest', 'package'], 'core_projects': ['scoop']})
