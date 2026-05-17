"""
GitHub Stars 分类器配置（统一入口）
====================================
此文件保持向后兼容，所有配置仍可通过 `from config import X` 导入。

为降低合并冲突和提升可维护性，配置已按主题拆分为子模块：
  - config_rules.py   : 平台/类型/生态分类规则
  - config_llm.py     : LLM API 与提示词
  - config_notion.py  : Notion 导出映射
  - config_notify.py  : 通知通道配置

如需修改，可直接编辑对应子模块；本文件会自动聚合导出。
"""

from .config_rules import (
    PLATFORM_RULES,
    TYPE_RULES,
    ECOLOGY_RULES,
    ECOLOGY_ROLES,
    LOCKED_ECOLOGIES,
)

from .config_llm import (
    LLM_CONFIG,
    LLM_SYSTEM_PROMPT,
)

from .config_notion import (
    NOTION_CONFIG,
)

from .config_notify import (
    NOTIFY_CONFIG,
    EMAIL_CONFIG,
    TELEGRAM_CONFIG,
    WECOM_CONFIG,
    QQ_CONFIG,
)
