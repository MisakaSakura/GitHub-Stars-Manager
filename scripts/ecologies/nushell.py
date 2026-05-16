#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nushell ecology rules"""

from . import register_ecology

register_ecology('Nushell', {'name_patterns': ['nushell'], 'desc_patterns': ['nushell', 'nu shell'], 'topic_patterns': ['nushell'], 'related_types': ['plugin', 'config', 'theme'], 'core_projects': ['nushell']})
