#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VS Code ecology rules"""

from . import register_ecology

register_ecology('VS Code', {'name_patterns': ['vscode', 'vs-code'], 'desc_patterns': ['vscode extension', 'visual studio code', 'vs code'], 'topic_patterns': ['vscode', 'vscode-extension'], 'related_types': ['extension', 'theme', 'icon-theme', 'snippet'], 'core_projects': ['vscode']})
