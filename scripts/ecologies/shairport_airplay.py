#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""shairport / AirPlay ecology rules"""

from . import register_ecology

register_ecology('shairport / AirPlay', {'name_patterns': ['shairport'], 'desc_patterns': ['shairport', 'airplay audio'], 'topic_patterns': ['shairport', 'airplay'], 'related_types': ['audio', 'player'], 'core_projects': ['shairport-sync']})
