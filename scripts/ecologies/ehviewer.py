#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EhViewer ecology rules"""

from . import register_ecology

register_ecology('EhViewer', {'name_patterns': ['ehviewer'], 'desc_patterns': ['ehviewer', 'e-hentai'], 'topic_patterns': ['ehviewer', 'e-hentai'], 'related_types': ['client', 'reader'], 'core_projects': ['ehviewer']})
