#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FFmpeg ecology rules"""

from . import register_ecology

register_ecology('FFmpeg', {'name_patterns': ['ffmpeg'], 'desc_patterns': ['ffmpeg', 'video processing', 'codec'], 'topic_patterns': ['ffmpeg'], 'related_types': ['wrapper', 'gui', 'binding'], 'core_projects': ['ffmpeg']})
