#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tailscale / WireGuard ecology rules"""

from . import register_ecology

register_ecology('Tailscale / WireGuard', {'name_patterns': ['tailscale', 'wireguard', 'headscale'], 'desc_patterns': ['tailscale', 'wireguard', 'mesh vpn', 'zero config vpn'], 'topic_patterns': ['tailscale', 'wireguard'], 'related_types': ['client', 'server', 'gui'], 'core_projects': ['tailscale', 'wireguard']})
