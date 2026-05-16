#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""React ecology rules"""

from . import register_ecology

register_ecology('React', {'name_patterns': ['react-'], 'desc_patterns': ['react component', 'react hook', 'for react'], 'topic_patterns': [], 'related_types': ['component', 'hook', 'boilerplate'], 'core_projects': ['react']})
