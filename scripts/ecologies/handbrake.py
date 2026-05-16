#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HandBrake ecology rules"""

from . import register_ecology

register_ecology('HandBrake', {'name_patterns': ['handbrake'], 'desc_patterns': ['handbrake', 'video transcoding'], 'topic_patterns': ['handbrake'], 'related_types': ['encoder', 'transcoder'], 'core_projects': ['handbrake']})
