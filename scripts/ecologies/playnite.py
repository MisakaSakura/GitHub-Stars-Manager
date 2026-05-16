#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Playnite ecology rules"""

from . import register_ecology

register_ecology('Playnite', {'name_patterns': ['playnite'], 'desc_patterns': ['playnite', 'game library manager'], 'topic_patterns': ['playnite'], 'related_types': ['launcher', 'library'], 'core_projects': ['playnite']})
