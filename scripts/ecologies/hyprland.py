#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hyprland ecology rules"""

from . import register_ecology

register_ecology('Hyprland', {'name_patterns': ['hypr', 'waybar', 'wofi', 'swww'], 'desc_patterns': ['hyprland', 'wayland compositor', 'hypr'], 'topic_patterns': ['hyprland', 'wayland'], 'related_types': ['dotfiles', 'config', 'theme', 'plugin'], 'core_projects': ['hyprland']})
