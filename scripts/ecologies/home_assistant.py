#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Home Assistant ecology rules"""

from . import register_ecology

register_ecology('Home Assistant', {'name_patterns': ['home-assistant', 'hass', 'homeassistant'], 'desc_patterns': ['home assistant', 'homeassistant'], 'topic_patterns': ['home-assistant', 'smart-home'], 'related_types': ['integration', 'addon', 'theme', 'card'], 'core_projects': ['home-assistant']})
