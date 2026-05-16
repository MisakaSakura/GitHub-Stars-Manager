#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EDK2 ecology rules"""

from . import register_ecology

register_ecology('EDK2', {'name_patterns': ['edk2'], 'desc_patterns': ['edk2', 'uefi firmware', 'tianocore'], 'topic_patterns': ['edk2', 'uefi-firmware'], 'related_types': ['port', 'driver'], 'core_projects': ['edk2']})
