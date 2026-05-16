#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""思维导图 / 白板 ecology rules"""

from . import register_ecology

register_ecology('思维导图 / 白板', {'name_patterns': ['mind-map', 'mindmap', 'xmind', 'whiteboard', 'drawnix'], 'desc_patterns': ['mind map', 'mind mapping', 'whiteboard', '思维导图', 'flowchart'], 'topic_patterns': ['mind-map', 'mindmap', 'whiteboard', 'flowchart'], 'related_types': ['editor', 'template', 'tool'], 'core_projects': ['mind-map']})
