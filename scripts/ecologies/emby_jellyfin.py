#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emby / Jellyfin ecology rules"""

from . import register_ecology

register_ecology('Emby / Jellyfin', {'name_patterns': ['emby', 'jellyfin'], 'desc_patterns': ['emby', 'jellyfin', 'media server', 'media-server'], 'topic_patterns': ['emby', 'jellyfin', 'media-server'], 'related_types': ['plugin', 'skin', 'server'], 'core_projects': ['emby', 'jellyfin']})
