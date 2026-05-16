#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ventoy ecology rules"""

from . import register_ecology

register_ecology('Ventoy', {'name_patterns': ['ventoy'], 'desc_patterns': ['ventoy', 'bootable usb', 'multiboot usb'], 'topic_patterns': ['ventoy', 'bootable-usb'], 'related_types': ['tool', 'gui'], 'core_projects': ['ventoy']})
