#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Git ecology rules"""

from . import register_ecology

register_ecology('Git', {'name_patterns': ['lazygit', 'git-extras', 'gitui'], 'desc_patterns': ['git commands', 'git tui', 'git client', 'git tools'], 'topic_patterns': ['git'], 'related_types': ['client', 'gui', 'tool'], 'core_projects': ['git']})
