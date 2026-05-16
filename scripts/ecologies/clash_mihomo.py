#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clash / Mihomo ecology rules"""

from . import register_ecology

register_ecology('Clash / Mihomo', {'name_patterns': ['clash', 'mihomo', 'sing-box'], 'desc_patterns': ['mihomo core', 'clash core', 'sing-box', 'clashmeta', 'clash meta', 'based on clash', 'mihomo'], 'topic_patterns': ['mihomo', 'sing-box', 'clash-meta'], 'related_types': ['gui', 'config', 'rule-set', 'dashboard'], 'core_projects': ['mihomo', 'clash', 'sing-box']})
