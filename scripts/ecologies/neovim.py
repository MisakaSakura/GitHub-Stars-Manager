#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Neovim ecology rules"""

from . import register_ecology

register_ecology('Neovim', {'name_patterns': ['nvim', 'neovim'], 'desc_patterns': ['neovim', 'nvim plugin', 'vim plugin'], 'topic_patterns': ['neovim', 'vim'], 'related_types': ['plugin', 'colorscheme', 'config', 'lsp'], 'core_projects': ['neovim']})
