#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vue ecology rules"""

from . import register_ecology

register_ecology('Vue', {'name_patterns': ['vue-', 'nuxt'], 'desc_patterns': ['vue component', 'vue plugin', 'for vue', 'nuxt', 'vuejs'], 'topic_patterns': [], 'related_types': ['component', 'plugin', 'boilerplate'], 'core_projects': ['vue', 'nuxt']})
