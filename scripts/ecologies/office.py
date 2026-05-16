#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Office ecology rules"""

from . import register_ecology

register_ecology('Office', {'name_patterns': ['office-tool'], 'desc_patterns': ['office tool', 'microsoft office', 'office 365', 'office deployment'], 'topic_patterns': ['office', 'office-365', 'msoffice'], 'related_types': ['tool', 'activator', 'installer'], 'core_projects': ['office']})
