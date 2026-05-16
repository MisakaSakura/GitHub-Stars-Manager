#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yt-dlp ecology rules"""

from . import register_ecology

register_ecology('yt-dlp', {'name_patterns': ['yt-dlp', 'youtube-dl'], 'desc_patterns': ['yt-dlp', 'youtube downloader', 'video downloader', 'based on yt-dlp'], 'topic_patterns': ['yt-dlp', 'youtube-downloader'], 'related_types': ['downloader', 'gui'], 'core_projects': ['yt-dlp']})
