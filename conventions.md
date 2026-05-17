# GitHub Stars Classifier — 全局一致性规范

**版本**: 1.0  
**生效日期**: 2026-05-17  
**适用范围**: `scripts/` 下全部 Python 模块、`tests/`、CI workflow

---

## 目录

1. [数据模型规范](#1-数据模型规范)
2. [存储层接口规范](#2-存储层接口规范)
3. [分类器接口规范](#3-分类器接口规范)
4. [异常处理规范](#4-异常处理规范)
5. [Pipeline 阶段规范](#5-pipeline-阶段规范)
6. [命名与导入规范](#6-命名与导入规范)
7. [配置规范](#7-配置规范)
8. [日志规范](#8-日志规范)
9. [版本控制](#9-版本控制)

---

## 1. 数据模型规范

### 1.1 Dataclass 设计原则

- **所有数据模型必须使用 `@dataclass`**，禁止使用裸 `dict` 传递结构化数据
- **默认值必须集中定义**：默认字符串值应在 `config_rules.py` 中定义为常量，禁止在模型中硬编码
- **必选字段**：`full_name`、`name`、`owner` 为必填，其余提供合理默认值

```python
# ✅ 正确
from config_rules import DEFAULT_LANGUAGE

@dataclass
class StarItem:
    full_name: str
    name: str
    owner: str
    language: str = DEFAULT_LANGUAGE  # 集中定义

# ❌ 错误
@dataclass
class StarItem:
    language: str = "文档 / 无代码"  # 硬编码
```

### 1.2 序列化规范

所有 dataclass 必须提供 `to_dict()` 和 `from_dict()` 方法，且遵循以下约定：

| 方法 | 实现要求 | 原因 |
|------|----------|------|
| `to_dict()` | 使用 `{k: getattr(self, k) for k in self.__dataclass_fields__}` | 浅拷贝，性能最优，避免 `asdict()` 的递归开销 |
| `from_dict()` | 使用 `cls.__dataclass_fields__` 过滤未知字段 | 向前兼容，忽略未来新增字段 |
| `from_dict()` | 对缺失字段提供兜底默认值 | 向后兼容，旧数据无新字段时不报错 |

```python
@dataclass
class MyModel:
    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict) -> "MyModel":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        # 兜底：旧数据可能缺失的字段
        if not filtered.get("created_at"):
            filtered["created_at"] = datetime.now(timezone.utc).isoformat()
        return cls(**filtered)
```

### 1.3 时间戳规范

- **所有时间戳使用 ISO 8601 格式**（`datetime.now(timezone.utc).isoformat()`）
- **禁止比较 naive datetime 与 aware datetime**：统一附加 `timezone.utc`
- **解析时兼容无 tz 的旧数据**：遇到 `tzinfo is None` 时自动替换为 `timezone.utc`

```python
# ✅ 正确
dt = datetime.fromisoformat(ts)
if dt.tzinfo is None:
    dt = dt.replace(tzinfo=timezone.utc)

# ❌ 错误
dt = datetime.fromisoformat(ts)  # naive/aware 比较会抛 TypeError
if datetime.now(timezone.utc) - dt >= timedelta(days=7):  # 可能崩溃
```

---

## 2. 存储层接口规范

### 2.1 Repository 抽象基类（完整契约）

所有存储实现必须实现以下完整接口，禁止省略任何方法：

```python
class Repository(ABC):
    # --- 数据操作 ---
    @abstractmethod
    def get(self, key: str) -> Any | None: pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None: pass

    @abstractmethod
    def delete(self, key: str) -> bool: pass

    @abstractmethod
    def keys(self) -> Iterator[str]: pass

    @abstractmethod
    def values(self) -> Iterator[Any]: pass

    @abstractmethod
    def items(self) -> Iterator[tuple[str, Any]]: pass

    @abstractmethod
    def save(self) -> None: pass

    @abstractmethod
    def __len__(self) -> int: pass

    # --- 元数据操作 ---
    @abstractmethod
    def meta_get(self, key: str, default=None): pass

    @abstractmethod
    def meta_set(self, key: str, value) -> None: pass

    @abstractmethod
    def meta_save(self) -> None: pass

    # --- 生命周期 ---
    @abstractmethod
    def close(self) -> None: pass
```

### 2.2 实现要求

| 要求 | 说明 |
|------|------|
| `set()` 类型验证 | 接受 `ModelType \| dict`，dict 时自动转换为模型实例 |
| `delete()` 返回值 | `True` = 成功删除，`False` = key 不存在 |
| `save()` 原子性 | 使用 `atomic_write` 或数据库事务，禁止直接覆盖 |
| `close()` 资源释放 | 释放文件句柄、数据库连接、Session 等资源 |
| `meta_*` 语义 | `meta_get`/`meta_set` 操作内存中的元数据，`meta_save` 持久化 |

### 2.3 适配器规范

`JSONStarsRepository` / `JSONAIRepository` 等适配器必须：
- 代理所有操作到底层后端的方法，**禁止直接操作底层 `_backend.data`**
- 提供 `backend` property 仅用于向后兼容，标记为 `@property` 并添加弃用说明

```python
# ✅ 正确
class JSONStarsRepository(Repository):
    def delete(self, key: str) -> bool:
        return self._backend.delete(key)  # 代理到后端方法

# ❌ 错误
class JSONAIRepository(Repository):
    def delete(self, key: str) -> bool:
        if self._backend.get(key) is not None:
            del self._backend.data[key]  # 直接操作底层 dict
            return True
        return False
```

---

## 3. 分类器接口规范

### 3.1 分类器抽象

```python
class BaseClassifier(ABC):
    """分类器统一接口"""

    @abstractmethod
    def classify_platform(self, item: dict) -> str:
        """返回平台分类字符串，无匹配时返回 DEFAULT_PLATFORM"""
        pass

    @abstractmethod
    def classify_type(self, item: dict) -> str:
        """返回类型分类字符串，无匹配时返回 DEFAULT_TYPE"""
        pass

    @abstractmethod
    def classify_ecology(self, item: dict) -> tuple[str | None, str | None]:
        """返回 (ecology, ecology_role)，无匹配时返回 (None, None)"""
        pass
```

### 3.2 返回值语义

| 分类维度 | 无匹配返回值 | 说明 |
|----------|-------------|------|
| `platform` | `"其他 / 未分类"` | 必须返回字符串，不能是 None |
| `type` | `"其他 / 未分类"` | 必须返回字符串，不能是 None |
| `ecology` | `None` | 返回 None 表示未匹配任何生态 |
| `ecology_role` | `None` | 返回 None 表示未匹配任何角色 |

### 3.3 LLM 分类器接口

```python
class LLMClassifier:
    def classify(self, item: dict) -> dict | None:
        """单条分类，失败时返回 None"""

    def classify_batch(self, items: list[dict], *, fallback: bool = False, round_label: str = "") -> dict[str, dict]:
        """批量分类，返回 {full_name: result_dict}"""

    def summarize(self, text: str, *, system_prompt: str | None = None, max_tokens: int | None = None) -> str | None:
        """文本摘要，失败时返回 None"""
```

**注意**：`classify_batch` 返回的 dict key 必须是 `"owner/repo"` 格式，与 `engine.py` 中 `key = f"{item['owner']['login']}/{item['name']}"` 保持一致。

---

## 4. 异常处理规范

### 4.1 异常分层

```
Exception
├── RuntimeError
│   └── PipelineStageError        # Pipeline 阶段执行失败
├── HTTPClientError               # HTTP 请求失败（重试耗尽）
├── GitHubAPIError                # GitHub API 相关错误
│   ├── GitHubAuthError           # 401 Token 无效
│   ├── GitHubRateLimitError      # 403 速率限制
│   └── GitHubServerError         # 5xx 服务端错误
└── ValueError                    # 输入数据格式错误
```

### 4.2 异常抛出规则

| 场景 | 应抛出的异常 | 说明 |
|------|-------------|------|
| HTTP 重试耗尽 | `HTTPClientError` | 包含原始错误消息（已脱敏） |
| GitHub 401 | `GitHubAuthError` | 上层可提示用户检查 Token |
| GitHub 403 | `GitHubRateLimitError` | 上层可提示稍后重试 |
| GitHub 5xx | `GitHubServerError` | 上层可自动重试整个流程 |
| Pipeline 阶段失败 | `PipelineStageError` | 包含阶段名和原始异常 |
| 输入数据格式错误 | `ValueError` / `TypeError` | 具体问题具体说明 |

### 4.3 异常捕获规则

- **底层方法**（如 `HTTPClient.request()`）只捕获自己处理得了的异常，其余向上冒泡
- **中层封装**（如 `GitHubAPI._get()`）必须捕获底层异常并转换为自己的异常类型
- **上层入口**（如 `Pipeline.run()`）捕获所有异常并记录日志，决定是继续还是终止

```python
# ✅ 正确：GitHubAPI 捕获 HTTPClientError 并转换
class GitHubAPI:
    def _get(self, endpoint, params=None):
        try:
            code, body = self.client.request(url, headers=self.headers, retries=3)
        except HTTPClientError as e:
            log(f"网络请求失败: {e}", "ERROR")
            raise GitHubServerError(f"无法连接到 GitHub API: {e}")
        # ... 处理 status code

# ❌ 错误：让 HTTPClientError 直接冒泡到调用方
class GitHubAPI:
    def _get(self, endpoint, params=None):
        code, body = self.client.request(url, headers=self.headers, retries=3)
        # 调用方可能不知道 HTTPClientError 的存在
```

### 4.4 错误消息脱敏

任何包含网络请求的错误消息必须经过 `_sanitize_error()` 处理：

```python
# 必须脱敏的内容：
# - URL 中的 token/key/api_key 参数
# - Authorization header 中的 Bearer token
# - 配置文件中的 API key
```

---

## 5. Pipeline 阶段规范

### 5.1 阶段函数签名

所有 Pipeline 阶段函数必须遵循以下签名：

```python
def stage_name(ctx: PipelineContext) -> None | bool:
    """
    Pipeline 阶段函数。

    Args:
        ctx: Pipeline 共享上下文

    Returns:
        None: 正常执行完毕，继续下一阶段
        True: 要求 Pipeline 提前终止（如 import_stage 导入后直接退出）
    """
```

**禁止**：
- 禁止在 stage 中直接调用 `sys.exit()`
- 禁止 stage 函数返回 `False`（语义不明确）
- 禁止 stage 函数修改 `ctx.args`（只读）

### 5.2 上下文访问规范

```python
# ✅ 正确：使用 getattr 安全访问
output = getattr(ctx.args, 'output', './docs')

# ✅ 正确：检查 None 后再使用
if ctx.ai_db:
    ctx.ai_db.save()

# ❌ 错误：直接访问可能不存在的属性
output = ctx.args.output  # 可能 AttributeError

# ❌ 错误：不检查 None
ctx.ai_db.save()  # 如果 ai_db 未初始化，NPE
```

### 5.3 依赖声明

阶段注册时必须声明依赖，依赖必须是已注册的阶段名：

```python
# ✅ 正确
_STAGE_REGISTRY = [
    ("setup", ".stages.setup_stage", "setup_stage", []),
    ("fetch", ".stages.fetch_stage", "fetch_stage", ["setup"]),
    ("classify", ".stages.classify_stage", "classify_stage", ["fetch", "enrich"]),
]
```

### 5.4 阶段执行顺序

`StageRegistry.run()` 必须按依赖拓扑排序后的顺序执行，而非注册顺序。拓扑排序确保：
1. 所有依赖在消费前已执行
2. 循环依赖在注册时即被检测并报错

---

## 6. 命名与导入规范

### 6.1 模块命名

| 类型 | 命名规则 | 示例 |
|------|----------|------|
| 数据模型 | `models.py` / `*_models.py` | `models.py`, `ai_database.py` |
| 存储实现 | `*_backend.py` | `json_backend.py`, `sqlite_backend.py` |
| Pipeline 阶段 | `*_stage.py` | `fetch_stage.py`, `classify_stage.py` |
| 工具模块 | 动词/名词，简洁 | `utils.py`, `http_client.py` |
| 配置文件 | `config_*.py` | `config_rules.py`, `config_llm.py` |
| 测试文件 | `test_*.py` | `test_engine.py`, `test_database.py` |

### 6.2 导入方式

```python
# ✅ 正确：模块内使用相对导入
from .base import Repository
from .cache import TTLCache

# ✅ 正确：跨模块使用绝对导入（在 scripts/ 根目录）
from models import StarItem
from utils import log

# ✅ 正确：根级聚合入口使用绝对导入
from config_rules import PLATFORM_RULES

# ❌ 错误：根级模块使用相对导入
from .config_rules import PLATFORM_RULES  # 直接运行脚本时无包上下文，ImportError
```

**规则**：
- 包内模块（如 `llm/` 子包）使用相对导入 `from .module import X`
- 根级模块间使用绝对导入 `from module import X`
- `config.py` 是聚合入口，使用绝对导入（因其职责就是聚合）

### 6.3 常量命名

| 类型 | 命名规则 | 示例 |
|------|----------|------|
| 模块级常量 | `UPPER_SNAKE_CASE` | `RULES_VERSION`, `DEFAULT_BATCH_SIZE` |
| 类级常量 | `UPPER_SNAKE_CASE` | `TOPIC_WEIGHT_MULTIPLIER` |
| 私有常量 | `_UPPER_SNAKE_CASE` | `_VALID_COL_NAME` |
| 配置 dict | `模块名_CONFIG` | `LLM_CONFIG`, `NOTION_CONFIG` |

---

## 7. 配置规范

### 7.1 配置来源优先级（从高到低）

```
1. CLI 显式参数（--llm-key, --llm-model）
2. 环境变量（LLM_PRESET, LLM_KEY）
3. 预设配置（--llm-preset → PROVIDER_PRESETS / CUSTOM_PRESETS）
4. 配置文件（config_llm.py 中的 LLM_CONFIG）
5. 内置默认值
```

### 7.2 预设配置规范

```python
# ✅ 正确：预设包含完整的 provider + base + model
PROVIDER_PRESETS = {
    "openai": {
        "provider": "openai",
        "api_base": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
}

# ✅ 正确：自定义预设通过 CUSTOM_PRESETS 扩展，同名覆盖内置
CUSTOM_PRESETS = {
    "mycompany": {
        "provider": "openai",
        "api_base": "https://llm.mycompany.com/v1",
        "model": "company-model-v1",
    },
}
```

### 7.3 环境变量预设

```bash
# 格式：name|provider|base|model[;name|provider|base|model...]
export LLM_PRESETS="mycompany|openai|https://llm.mycompany.com/v1|company-v1"
```

---

## 8. 日志规范

### 8.1 日志级别使用

| 级别 | 使用场景 | 前缀 |
|------|----------|------|
| `INFO` | 一般信息，如配置加载完成 | ℹ️ |
| `OK` | 操作成功完成 | ✅ |
| `WARN` | 非致命问题，如网络重试、缓存失效 | ⚠️ |
| `ERROR` | 致命错误，操作失败 | ❌ |
| `STEP` | 阶段性进度，如"开始分类" | 🔄 |

### 8.2 日志内容规范

```python
# ✅ 正确：包含操作对象和结果
log(f"加载数据库: {len(db.data)} 个项目", "OK")
log(f"处理 {full_name} 失败: {e}", "ERROR")

# ✅ 正确：异常细分，不同异常不同处理
except json.JSONDecodeError as e:
    log(f"JSON 解析失败: {e}", "WARN")
except OSError as e:
    log(f"文件读取失败: {e}", "WARN")

# ❌ 错误：过于宽泛的异常捕获
except Exception as e:
    log(f"出错了: {e}", "ERROR")  # 无法定位问题

# ❌ 错误：裸 except
except:
    pass  # 完全吞没异常
```

---

## 9. 版本控制

### 9.1 规则版本

`RULES_VERSION` 定义在 `config_rules.py`，格式：`YYYY-MM-DD-变更描述`

- 平台/类型分类体系发生**不兼容变更**时递增
- 仅新增生态（不修改现有规则）时**不递增**
- 用于 feedback 系统判断旧修正是否仍适用

### 9.2 缓存版本

`llm/cache.py` 中的 `TTLCache` 使用 `rules_version` 校验：

```python
cache = TTLCache(".llm_cache.json", ttl_seconds=0, rules_version=RULES_VERSION)
```

- 规则版本变化时自动清空旧缓存
- 防止规则更新后仍使用旧分类结果

---

## 附录 A：接口对照速查表

### A.1 存储层完整接口对照

| 操作 | StarsDB | AIDatabase | SQLiteStarsRepository | JSONStarsRepository | JSONAIRepository |
|------|---------|------------|----------------------|---------------------|------------------|
| `get` | ✅ StarItem\|None | ✅ AIResult\|None | ✅ StarItem\|None | ✅ Any\|None | ✅ Any\|None |
| `set` | ✅ StarItem\|dict | ✅ AIResult | ✅ StarItem\|dict | ✅ Any | ✅ Any |
| `delete` | ✅ bool | ✅ bool | ✅ bool | ✅ bool | ✅ bool |
| `keys` | ✅ Iterator | ✅ Iterator | ✅ Iterator | ✅ Iterator | ✅ Iterator |
| `values` | ✅ Iterator | ✅ Iterator | ✅ Iterator | ✅ Iterator | ✅ Iterator |
| `items` | ✅ Iterator | ✅ Iterator | ✅ Iterator | ✅ Iterator | ✅ Iterator |
| `save` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `__len__` | ✅ int | ✅ int | ✅ int | ✅ int | ✅ int |
| `meta_get` | ✅ | ❌ N/A | ✅ | ✅ | ❌ **空实现** |
| `meta_set` | ✅ | ❌ N/A | ✅ | ✅ | ❌ **空实现** |
| `meta_save` | ✅ | ❌ N/A | ✅ | ✅ | ❌ **空实现** |
| `close` | ❌ | ❌ | ✅ | ❌ | ❌ |

**注**：所有存储实现已对齐完整接口契约。

### A.2 分类器返回类型对照

| 分类器 | 方法 | 输入 | 输出 | 无匹配返回值 |
|--------|------|------|------|-------------|
| RuleClassifier | classify_platform | dict | str | "其他 / 未分类" |
| RuleClassifier | classify_type | dict | str | "其他 / 未分类" |
| RuleClassifier | classify_ecology | dict | tuple | (None, None) |
| LLMClassifier | classify | dict | dict\|None | None |
| LLMClassifier | classify_batch | list[dict] | dict[str, dict] | {} |

---

## 附录 B：修订记录

| 版本 | 日期 | 修订内容 |
|------|------|----------|
| 1.1 | 2026-05-17 | 更新导入规范（config.py 绝对导入示例）；补充 AIDatabase 完整接口；移除 Phase 5 遗留标记 |
| 1.0 | 2026-05-17 | 初始版本，基于全局一致性审查建立 |
