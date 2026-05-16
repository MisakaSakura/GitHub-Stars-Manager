#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zsh / Oh-My-Zsh ecology rules"""

from . import register_ecology

register_ecology('Zsh / Oh-My-Zsh', {'name_patterns': ['zsh', 'oh-my-zsh', 'powerlevel'], 'desc_patterns': ['zsh', 'oh-my-zsh', 'zsh plugin', 'shell theme'], 'topic_patterns': ['zsh', 'oh-my-zsh'], 'related_types': ['plugin', 'theme', 'config'], 'core_projects': ['oh-my-zsh']})
