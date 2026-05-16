#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V2Ray ecology rules"""

from . import register_ecology

register_ecology('V2Ray', {'name_patterns': ['v2ray', 'v2fly'], 'desc_patterns': ['v2ray', 'v2fly', 'v2ray core', 'geosite'], 'topic_patterns': ['v2ray', 'v2fly'], 'related_types': ['core', 'config', 'rule'], 'core_projects': ['v2ray-core']})
