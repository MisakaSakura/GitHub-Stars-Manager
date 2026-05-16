#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stable Diffusion ecology rules"""

from . import register_ecology

register_ecology('Stable Diffusion', {'name_patterns': ['stable-diffusion', 'sd-webui', 'comfyui', 'controlnet', 'fooocus'], 'desc_patterns': ['stable diffusion', 'comfyui', 'diffusion model', 'text-to-image', 'image generation'], 'topic_patterns': ['stable-diffusion', 'comfyui', 'text-to-image', 'image-generation'], 'related_types': ['webui', 'model', 'extension', 'checkpoint'], 'core_projects': ['stable-diffusion-webui', 'comfyui']})
