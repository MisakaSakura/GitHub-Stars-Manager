#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qBittorrent ecology rules"""

from . import register_ecology

register_ecology('qBittorrent', {'name_patterns': ['qbittorrent', 'qbit'], 'desc_patterns': ['qbittorrent', 'bt client', 'qbittorrent web ui'], 'topic_patterns': ['qbittorrent'], 'related_types': ['theme', 'plugin', 'web-ui'], 'core_projects': ['qbittorrent']})
