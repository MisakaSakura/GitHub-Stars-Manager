#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RVC / AI Voice ecology rules"""

from . import register_ecology

register_ecology('RVC / AI Voice', {'name_patterns': ['rvc', 'so-vits-svc', 'fish-speech', 'voice-conversion'], 'desc_patterns': ['voice conversion', 'singing voice conversion', 'tts', 'text-to-speech', 'voice clone'], 'topic_patterns': ['voice-conversion', 'tts', 'rvc', 'text-to-speech'], 'related_types': ['model', 'gui', 'webui'], 'core_projects': ['retrieval-based-voice-conversion-webui', 'so-vits-svc', 'fish-speech']})
