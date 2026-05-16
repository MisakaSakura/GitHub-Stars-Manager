#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notion / AppFlowy ecology rules"""

from . import register_ecology

register_ecology('Notion / AppFlowy', {'name_patterns': ['notionnext', 'appflowy', 'affine'], 'desc_patterns': ['notion alternative', 'notion-powered', 'knowledge base', 'second brain'], 'topic_patterns': ['notion', 'notion-alternative', 'knowledge-base'], 'related_types': ['theme', 'template', 'plugin', 'blog'], 'core_projects': ['appflowy', 'affine']})
