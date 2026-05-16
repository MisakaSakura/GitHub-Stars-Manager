#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rufus ecology rules"""

from . import register_ecology

register_ecology('rufus', {'name_patterns': ['rufus'], 'desc_patterns': ['rufus', 'usb formatting', 'bootable drives'], 'topic_patterns': ['rufus', 'bootable-drives'], 'related_types': ['tool'], 'core_projects': ['rufus']})
