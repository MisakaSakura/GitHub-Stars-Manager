#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Homebrew ecology rules"""

from . import register_ecology

register_ecology('Homebrew', {'name_patterns': ['homebrew'], 'desc_patterns': ['homebrew', 'brew', 'macos package manager'], 'topic_patterns': ['homebrew'], 'related_types': ['formula', 'cask', 'tap'], 'core_projects': ['brew']})
