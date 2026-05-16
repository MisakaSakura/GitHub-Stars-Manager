#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AList ecology rules"""

from . import register_ecology

register_ecology('AList', {'name_patterns': ['alist', 'openlist'], 'desc_patterns': ['alist', 'file list program', 'cloud storage aggregation'], 'topic_patterns': ['alist', 'webdav'], 'related_types': ['client', 'web-ui', 'mount'], 'core_projects': ['alist']})
