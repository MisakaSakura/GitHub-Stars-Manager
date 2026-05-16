#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LSPosed ecology rules"""

from . import register_ecology

register_ecology('LSPosed', {'name_patterns': ['lsposed', 'xposed'], 'desc_patterns': ['lsposed', 'xposed framework', 'android hook'], 'topic_patterns': ['lsposed', 'xposed'], 'related_types': ['module', 'framework'], 'core_projects': ['lsposed']})
