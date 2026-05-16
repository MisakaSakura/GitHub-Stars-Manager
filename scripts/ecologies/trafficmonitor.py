#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TrafficMonitor ecology rules"""

from . import register_ecology

register_ecology('TrafficMonitor', {'name_patterns': ['trafficmonitor'], 'desc_patterns': ['traffic monitor', 'network speed', 'cpu monitor'], 'topic_patterns': ['traffic-monitor', 'network-monitor'], 'related_types': ['tool', 'widget'], 'core_projects': ['trafficmonitor']})
