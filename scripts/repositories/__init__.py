#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据访问层：Repository 模式，抽象存储后端"""

from .base import Repository
from .json_backend import JSONStarsRepository, JSONAIRepository
from .sqlite_backend import SQLiteStarsRepository

__all__ = ["Repository", "JSONStarsRepository", "JSONAIRepository", "SQLiteStarsRepository"]
