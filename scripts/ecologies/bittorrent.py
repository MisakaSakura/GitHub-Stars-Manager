#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BitTorrent ecology rules"""

from . import register_ecology

register_ecology('BitTorrent', {'name_patterns': ['trackerslist'], 'desc_patterns': ['bittorrent tracker', 'torrent tracker', 'public tracker'], 'topic_patterns': ['bittorrent', 'bittorrent-tracker', 'torrent'], 'related_types': ['tracker', 'list'], 'core_projects': ['trackerslist']})
