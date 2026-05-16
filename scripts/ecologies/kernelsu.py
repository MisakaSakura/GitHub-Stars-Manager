#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KernelSU ecology rules"""

from . import register_ecology

register_ecology('KernelSU', {'name_patterns': ['kernelsu'], 'desc_patterns': ['kernelsu', 'android root', 'kernel-based root'], 'topic_patterns': ['kernelsu', 'android-root'], 'related_types': ['module', 'manager'], 'core_projects': ['kernelsu']})
