#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Docker ecology rules"""

from . import register_ecology

register_ecology('Docker', {'name_patterns': ['docker'], 'desc_patterns': ['dockerfile', 'docker-compose'], 'topic_patterns': ['docker-compose', 'containers'], 'related_types': ['image', 'compose', 'registry'], 'core_projects': ['docker', 'moby']})
