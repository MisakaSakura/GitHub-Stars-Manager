#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""localsend ecology rules"""

from . import register_ecology

register_ecology('localsend', {'name_patterns': ['localsend'], 'desc_patterns': ['localsend', 'cross-platform file sharing', 'airdrop alternative'], 'topic_patterns': ['localsend', 'file-sharing'], 'related_types': ['app', 'client'], 'core_projects': ['localsend']})
