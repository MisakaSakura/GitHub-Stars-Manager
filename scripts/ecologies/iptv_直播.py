#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IPTV / 直播 ecology rules"""

from . import register_ecology

register_ecology('IPTV / 直播', {'name_patterns': ['iptv', 'my-tv', 'mytv', 'simple-live'], 'desc_patterns': ['iptv', '电视直播', 'live streaming', 'tv live'], 'topic_patterns': ['iptv', 'live-streaming'], 'related_types': ['player', 'client', 'app'], 'core_projects': ['iptv']})
