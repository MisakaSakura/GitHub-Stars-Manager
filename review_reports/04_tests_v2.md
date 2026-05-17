# 批次4审查报告：测试层

## 审查范围

| 序号 | 文件 | 说明 |
|------|------|------|
| 1 | `tests/test_github_api.py` | GitHub API 错误处理、工具方法、分页测试 |
| 2 | `tests/test_http_client.py` | HTTPClient urllib/requests 双后端测试 |
| 3 | `tests/test_models.py` | StarItem 数据模型测试 |
| 4 | `tests/test_database.py` | StarsDB JSON 数据库测试 |
| 5 | `tests/test_repositories.py` | Repository 模式（JSON + SQLite）集成测试 |
| 6 | `tests/test_classifiers.py` | RuleClassifier 分类规则测试 |
| 7 | `tests/test_engine.py` | IncrementalEngine 增量更新引擎测试 |
| 8 | `tests/test_integration.py` | ReportGenerator / ReleaseTracker 集成测试 |
| 9 | `tests/test_lists_manager.py` | ListsManager 测试 |
| 10 | `tests/test_notify.py` | 多通道通知系统测试 |
| 11 | `tests/test_notion.py` | NotionExporter 测试 |
| 12 | `tests/test_trackers.py` | ReleaseTracker / ForkTracker 测试 |
| 13 | `tests/test_import_helper.py` | FirstRunHelper 导入辅助测试 |
| 14 | `tests/test_correct_command.py` | CorrectCommand 修正命令测试 |
| 15 | `tests/test_sqlite_backend.py` | SQLite 后端独立测试 |
| 16 | `tests/test_feedback_loop.py` | FeedbackLoop 版本控制与冲突检测测试 |
| 17 | `tests/test_new_pipeline.py` | Pipeline 插件化架构测试 |
| 18 | `tests/test_classifier.py` | CLI mode/preset 映射测试 |

---

## P0 — 阻塞级（3项）

| # | 文件 | 行号 | 问题描述 | 影响 | 修复建议 |
|---|------|------|----------|------|----------|
| P0-1 | `tests/test_engine.py` | 165 | `@patch("config.LOCKED_ECOLOGIES")` 补丁路径错误。`config.py` 中 `LOCKED_ECOLOGIES` 被 `engine.py` 的 `_is_ecology_locked()` 在运行时通过 `from config import LOCKED_ECOLOGIES` 导入，patch 应作用于 `engine.LOCKED_ECOLOGIES` 而非 `config.LOCKED_ECOLOGIES` | 测试可能通过错误的 mock 路径导致实际未隔离 `LOCKED_ECOLOGIES`，测试不可靠，可能在真实配置变化时失败 | 改为 `@patch("engine.LOCKED_ECOLOGIES", ["PyTorch"])` 或 `@patch.dict("engine.LOCKED_ECOLOGIES", ...)` |
| P0-2 | `tests/test_engine.py` | 187-232 | `test_llm_skips_existing_within_interval` 和 `test_llm_reanalyzes_existing_outside_interval` 使用 `tempfile.mkdtemp()` 创建临时目录但未在 tearDown 中清理，且 `ai_db` 文件句柄未关闭 | 临时文件泄漏，多次运行后磁盘堆积；CI 环境可能因磁盘空间不足失败 | 添加 `self.tmpdir` 清理逻辑，使用 `self.addCleanup(shutil.rmtree, tmpdir)` 或 `tempfile.TemporaryDirectory` 上下文管理器 |
| P0-3 | `tests/test_database.py` | 20-27 | `tearDown` 使用 `os.rmdir(self.tmpdir)` 删除目录，但如果目录中有未预期的文件（如 `.meta.json`、`.lock`、`.tmp`），`rmdir` 会因目录非空而失败 | tearDown 失败导致后续测试受影响，测试套件不稳定 | 改用 `shutil.rmtree(self.tmpdir, ignore_errors=True)` 替代手动文件遍历删除 |

---

## P1 — 重要（16项）

| # | 文件 | 行号 | 问题描述 | 影响 | 修复建议 |
|---|------|------|----------|------|----------|
| P1-1 | `tests/test_github_api.py` | 16-44 | `test_auth_error`、`test_rate_limit_error`、`test_404_returns_none` 均 mock `github_api.HTTPClient` 类本身，但 `GitHubAPI.__init__` 中 `self.client = HTTPClient()` 是实例化调用。mock 类返回 MagicMock 实例，但 `request()` 方法在 MagicMock 上设置，实际 `HTTPClient()` 返回的 MagicMock 实例行为正确，但这种方式 mock 的是类而非方法，耦合度过高 | 测试与 `HTTPClient` 的内部实现耦合，如果 `GitHubAPI` 改为使用模块级函数或不同的 HTTP 客户端，测试需要大面积修改 | 改为 mock `github_api.HTTPClient.request` 方法，或 mock `GitHubAPI.client` 属性 |
| P1-2 | `tests/test_http_client.py` | 42-58 | `test_requests_post_json` 使用 `with patch.object(hc.HTTPClient, "_session", mock_session)` 在类上设置 `_session`，但 `_session` 是类变量，此修改会影响后续所有测试 | 全局状态污染，如果后续测试也使用 requests 后端，可能因 `_session` 被修改而产生不可预期的行为 | 在 `tearDown` 中重置 `HTTPClient._session = None`，或使用 `patch.object` 作为上下文管理器确保退出时恢复 |
| P1-3 | `tests/test_engine.py` | 52-65 | `MockDB` 的 `set()` 方法将 dict 转为 `StarItem`，但缺少 `save()`、`keys()`、`values()`、`items()`、`meta_get()`、`meta_set()`、`meta_save()` 等方法，与真实 `StarsDB` / `Repository` 接口不完全一致 | 测试使用的 mock 与真实接口不一致，可能掩盖真实集成问题 | 补充 mock 缺少的方法，或改用 `unittest.mock.create_autospec(StarsDB)` 自动生成接口一致的 mock |
| P1-4 | `tests/test_engine.py` | 134-163 | `test_llm_enhanced` 和 `test_llm_failed` 断言 `engine.llm_results` 包含特定键，但未验证 AI 数据库 (`ai_db`) 是否正确记录了结果 | 只测试了内存状态，未验证持久化行为，与 "AI 字段已迁移到独立 AI 数据库" 的注释不一致 | 补充断言验证 `ai_db.get(key)` 的返回值，或明确注释说明此处只测试引擎内部状态 |
| P1-5 | `tests/test_repositories.py` | 111-241 | `TestSQLiteStarsRepository` 缺少 `test_save_and_load`（已存在于 JSON 测试中但 SQLite 测试中未覆盖），且 `test_persistence` 与 `test_set_and_get` 重复 | SQLite 后端的 `save()` + 新实例加载流程未单独验证，与 JSON 后端测试不对称 | 添加独立的 `test_save_and_load` 方法，验证 `save()` 后新实例能正确加载；移除重复的 `test_persistence` |
| P1-6 | `tests/test_repositories.py` | 199-214 | `test_migrate_from_json` 使用 `json.dump([{...}], f)` 写入列表格式，但 StarsDB 实际存储格式也是列表，测试未验证迁移后 `is_fork`、`imported` 等字段是否正确转换 | 迁移逻辑覆盖不完整，可能遗漏字段映射 bug | 补充断言验证迁移后的完整字段，包括 `is_fork`、`imported`、`github_list_source` 等 |
| P1-7 | `tests/test_trackers.py` | 71-91 | `test_check_multiple_releases_in_week` 使用 `_future_date(3)` 等动态未来日期，但 `v1.0` 的 `published_at` 硬编码为 `"2024-01-01T00:00:00Z"`。时间窗口逻辑依赖 `last_release_checked`，但测试 item 未设置该字段 | 未设置 `last_release_checked` 时窗口回退到 `now - 7 days`，硬编码的 2024 日期必然在窗口外，但测试仍期望 `v1.2`、`v1.1` 被捕获——这依赖 `last_release_tag="v1.0"` 时的 `current_idx` 定位逻辑，而非时间窗口 | 明确注释测试意图（验证 `current_idx` 定位 + 中间版本捕获），或补充设置 `last_release_checked` 以完整测试时间窗口逻辑 |
| P1-8 | `tests/test_trackers.py` | 111-130 | `test_check_all_baseline_first_discovery` 使用 `datetime.now(timezone.utc).isoformat()` 作为 `first_seen`，`_is_newly_starred()` 判断 `<= timedelta(days=7)`。测试在 7 天后运行会因 `first_seen` 超过 7 天而失败 | 时间依赖导致测试在特定日期后变为 flaky | 使用固定未来日期（如 `_future_date()`）作为 `first_seen`，确保测试始终满足 `_is_newly_starred()` 条件 |
| P1-9 | `tests/test_integration.py` | 150-189 | `TestReleaseTrackerWithStarItem` 中 `test_check_updates_staritem_attributes` 断言 `item.last_release_tag` 被修改为 `"v2.0.0"`，但 `ReleaseTracker._check_candidates` 实际通过 `mutations` 列表在并发结束后统一回写，测试直接检查 item 属性 | 测试与实现细节耦合（知道 mutations 会回写 dict 属性），但如果实现改为不修改传入对象，测试会失败 | 明确测试契约：验证返回的 `updates` 列表内容，而非传入对象的副作用；或添加注释说明此测试验证 dataclass 可变性 |
| P1-10 | `tests/test_feedback_loop.py` | 123-125 | `TestDetectOverrideConflicts` 使用 `@patch("config_rules.RULES_VERSION", "test-v2")` 但 `FeedbackLoop._current_rules_version()` 内部读取的是 `config_rules.RULES_VERSION`，patch 路径正确。但 `detect_override_conflicts` 中 `rule = RuleClassifier()` 会触发 `RuleClassifier._load_learned_overrides()` 读取文件系统 | 测试隐式依赖文件系统（`learned_rules.json` 是否存在），如果文件存在且内容异常可能导致测试不稳定 | 在 `setUp` 中 mock `RuleClassifier._load_learned_overrides` 返回空 dict，或确保测试环境无 `learned_rules.json` |
| P1-11 | `tests/test_feedback_loop.py` | 316-365 | `TestStarsDBVersionBehavior` 在类级别 `@patch("database.RULES_VERSION")`，但 `StarsDB` 中不再使用 `RULES_VERSION`（P1-10 已移除自动填充），此测试实际上在测试一个已废弃的行为 | 测试维护过时逻辑，增加维护负担 | 移除 `TestStarsDBVersionBehavior` 测试类，或将其标记为 deprecated，因为 `StarsDB.set()` 不再涉及 `RULES_VERSION` |
| P1-12 | `tests/test_classifiers.py` | 15-76 | `TestRuleClassifier` 使用 `_make_item()` 返回 dict，但 `RuleClassifier` 实际接受的是 GitHub API 原始 dict 格式（含 `owner: {"login": ...}`）。测试中的 dict 格式正确，但未测试 `ItemFeatures.from_item()` 对缺失字段的容错 | 如果传入 item 缺少 `owner` 或 `description` 字段，`from_item()` 可能抛出异常，但无对应测试 | 添加边界测试：`test_from_item_missing_fields` 验证 `ItemFeatures.from_item({"name": "x"})` 不崩溃 |
| P1-13 | `tests/test_notion.py` | 42-64 | `test_create_page_success` 和 `test_create_page_failure_raises` mock `notion.HTTPClient` 类，但 `NotionExporter.__init__` 中 `self.client = HTTPClient()` 创建实例。mock 类后 `HTTPClient()` 返回 MagicMock，但测试未验证 `HTTPClient` 构造时是否传入了正确的 headers | 测试只验证了 `_create_page` 的行为，未验证 `NotionExporter` 初始化时 headers 的正确性 | 添加测试验证 `HTTPClient` 初始化时 `headers` 参数包含 `Authorization: Bearer key` 和 `Notion-Version` |
| P1-14 | `tests/test_notify.py` | 58-77 | `test_send_email` mock `notify.smtplib.SMTP`，但 `EmailNotifier.send()` 内部 `from config import EMAIL_CONFIG` 在方法内动态导入，patch 的 `EMAIL_CONFIG` 在类级别。如果 `EMAIL_CONFIG` 在模块加载时已被缓存，patch 可能不生效 | 动态导入的配置 patch 可能不可靠，取决于导入时机 | 将 `EMAIL_CONFIG` 的 patch 改为方法级别，或重构 `EmailNotifier` 接受配置参数注入（依赖注入） |
| P1-15 | `tests/test_import_helper.py` | 73-90 | `test_imports_items` 断言 `db.data["owner/repo1"]["manual_override"]` 为 True，但 `import_from_json` 返回的 dict 中 `manual_override` 被设为 `True`，而 MockDB 只是简单存储 dict，未转换为 `StarItem`。测试与真实 `StarsDB.set()` 行为不一致 | MockDB 与真实 DB 行为不一致（真实 DB 会将 dict 转为 StarItem），测试可能通过但真实场景行为不同 | 使用真实 `StarsDB` 或让 MockDB 的 `set()` 也执行 `StarItem.from_dict()` 转换 |
| P1-16 | `tests/test_new_pipeline.py` | 100-131 | `test_run_all_stages` 跳过 `fetch`、`enrich` 等阶段，但 `setup_stage` 会创建真实 `StarsDB` 和 `AIDatabase` 实例（mock 未生效），且 `args.db = "./test_db.json"` 会在当前目录创建真实文件 | 测试在文件系统中创建真实文件，可能污染工作目录，且 `shutil.rmtree` 未在 tearDown 中调用 | 使用 `tempfile.mkdtemp()` 生成临时 db 路径，并在 tearDown 中清理；或完全 mock `StarsDB` 和 `AIDatabase` |

---

## P2 — 建议（14项）

| # | 文件 | 行号 | 问题描述 | 影响 | 修复建议 |
|---|------|------|----------|------|----------|
| P2-1 | `tests/test_engine.py` | 30-42 | `_safe_int` 的测试分散在 `TestSafeInt` 类中，但 `_safe_int` 是 `engine.py` 的私有函数。同时 `import_helper.py` 也有同名 `_safe_int`，`test_import_helper.py` 也测试了该函数 | 重复测试同一功能的不同副本，维护成本高 | 提取 `_safe_int` 到 `utils.py` 作为公共工具函数，统一测试 |
| P2-2 | `tests/test_database.py` | 29-46 | `test_corrupted_file_rebuilds` 写入 `"not valid json"` 后验证 `len(db) == 0`，但未验证日志输出或异常捕获 | 测试只验证了结果，未验证错误处理路径的日志记录 | 可选：使用 `unittest.mock.patch("database.log")` 验证警告日志被触发 |
| P2-3 | `tests/test_database.py` | 74-81 | `test_get_returns_staritem` 和 `test_set_converts_dict_to_starItem` 的 docstring 中包含 "P1-9" 等内部 ticket 编号 | 测试代码中混入项目管理标记，降低可读性 | 移除 docstring 中的 ticket 编号，或将其移到注释中 |
| P2-4 | `tests/test_repositories.py` | 1-3 | 文件 docstring 为 `"Repository 模式集成测试 —— 验证 JSON 后端与 StarsDB 行为一致"`，但测试内容已扩展为包含 SQLite 后端和 AI Repository | docstring 与实际内容不符 | 更新 docstring 为 `"Repository 模式集成测试 —— JSON / SQLite / AI 后端行为验证"` |
| P2-5 | `tests/test_trackers.py` | 16-19 | `_future_date()` 辅助函数定义在测试文件顶部，但 `test_trackers.py` 和 `test_integration.py` 都使用了类似的未来日期逻辑 | 重复代码，如果日期格式要求变化需要多处修改 | 提取到 `tests/utils.py` 作为共享测试工具函数 |
| P2-6 | `tests/test_integration.py` | 50-68 | `_make_item()` 方法在每个测试类中重复定义（`TestReportGeneratorWithStarItem` 和 `TestReleaseTrackerWithStarItem` 都有类似逻辑） | 重复代码，维护成本高 | 提取为模块级辅助函数或测试基类 |
| P2-7 | `tests/test_notify.py` | 15-19 | `test_init_creates_channels` 同时 patch 4 个配置，但每个测试方法都重复类似的 patch 模式 | 装饰器堆叠导致视觉噪音，且配置耦合度高 | 使用 `setUp` 中的 `self.addCleanup` 统一设置，或创建测试基类封装常用 patch |
| P2-8 | `tests/test_notion.py` | 25-39 | `test_build_properties` 使用 `@patch("config.NOTION_CONFIG", {...})` 注入完整配置，但测试只验证了 5 种 property 类型 | 未覆盖 `rich_text`、`url` 等类型的构建逻辑 | 补充 `rich_text`、`url` 类型的测试用例 |
| P2-9 | `tests/test_correct_command.py` | 135-141 | `test_feedback_recorded` 只验证了 `feedback.json` 文件存在，未验证文件内容 | 测试覆盖不足，文件可能存在但内容为空或格式错误 | 补充断言：加载 `feedback.json` 并验证包含 `"owner/existing"` 条目 |
| P2-10 | `tests/test_classifier.py` | 16-32 | `FakeArgs` 类手动定义了 13 个属性，但 `_apply_mode` 可能访问更多属性。如果未来添加新属性，测试可能因 `AttributeError` 失败 | 维护成本高，容易遗漏新属性 | 使用 `unittest.mock.MagicMock()` 替代 `FakeArgs`，或基于 `argparse.Namespace` 动态设置属性 |
| P2-11 | `tests/test_classifier.py` | 269-301 | `TestRelativeTime` 和 `TestRenderReleaseBody` 测试的是 `report.py` 的函数，但放在 `test_classifier.py` 中 | 测试文件组织混乱，一个文件测试多个不相关模块 | 将 `TestRelativeTime` 和 `TestRenderReleaseBody` 移到 `test_report.py`（如果不存在则创建） |
| P2-12 | `tests/test_feedback_loop.py` | 140-148 | `test_no_conflicts_when_all_match` 使用 `MockDB` 但 `RuleClassifier` 实际会对 item 执行分类，由于 `MockDB.items()` 返回的 item 是 `StarItem`，`detect_override_conflicts` 中 `item.to_dict()` 可用，但 `RuleClassifier.classify_platform` 等需要 `{"name": ..., "topics": ...}` 格式 | `StarItem.to_dict()` 的格式与 `RuleClassifier` 期望的 GitHub API dict 格式不完全一致，但测试仍通过（因为字段名相同） | 添加注释说明 `StarItem.to_dict()` 的输出格式恰好满足 `RuleClassifier` 的输入要求 |
| P2-13 | `tests/test_sqlite_backend.py` | 124-181 | `TestSQLiteJSONParity` 的 `test_parity_with_json_backend` 只对比了 18 个字段，但 `StarItem` 有 25+ 个字段。未对比的字段包括 `llm_status`、`ai_summary`、`last_release_checked` 等 | 字段覆盖不完整，如果新增字段未同步到 SQLite schema，测试无法发现 | 扩展字段列表覆盖所有 `StarItem` 字段，或使用 `dataclasses.asdict()` 全量对比 |
| P2-14 | `tests/test_new_pipeline.py` | 191-219 | `test_setup_stage_first_run` 和 `test_setup_stage_existing_db` mock `StarsDB` 和 `AIDatabase`，但 `setup_stage` 内部可能调用 `FirstRunHelper.detect_first_run()` 和 `FirstRunHelper.import_from_json()`，mock 未验证这些调用 | 测试只验证了高层行为，未验证辅助函数的调用参数 | 可选：添加 `mock_first_run.detect_first_run.assert_called_once_with(...)` 等断言 |

---

## 按模块汇总

| 模块 | P0 | P1 | P2 | 关键问题 |
|------|-----|-----|-----|----------|
| `test_engine.py` | 2 | 4 | 1 | P0-1 mock 路径错误、P0-2 临时文件泄漏、P1-3 MockDB 接口不完整 |
| `test_database.py` | 1 | 0 | 2 | P0-3 tearDown 使用 rmdir 可能失败 |
| `test_trackers.py` | 0 | 2 | 1 | P1-8 时间依赖 flaky test |
| `test_repositories.py` | 0 | 2 | 1 | P1-5 SQLite 测试不对称、P1-6 迁移覆盖不完整 |
| `test_feedback_loop.py` | 0 | 2 | 1 | P1-10 文件系统隐式依赖、P1-11 测试过时逻辑 |
| `test_github_api.py` | 0 | 1 | 0 | P1-1 mock 耦合度过高 |
| `test_http_client.py` | 0 | 1 | 0 | P1-2 全局状态污染 |
| `test_integration.py` | 0 | 1 | 1 | P1-9 测试与实现细节耦合 |
| `test_classifiers.py` | 0 | 1 | 0 | P1-12 边界测试缺失 |
| `test_notion.py` | 0 | 1 | 1 | P1-13 headers 验证缺失 |
| `test_notify.py` | 0 | 1 | 1 | P1-14 动态导入 patch 不可靠 |
| `test_import_helper.py` | 0 | 1 | 0 | P1-15 MockDB 与真实 DB 行为不一致 |
| `test_new_pipeline.py` | 0 | 1 | 1 | P1-16 真实文件系统污染 |
| `test_correct_command.py` | 0 | 0 | 1 | P2-9 反馈内容验证缺失 |
| `test_classifier.py` | 0 | 0 | 2 | P2-10 FakeArgs 维护成本高、P2-11 测试文件组织混乱 |
| `test_sqlite_backend.py` | 0 | 0 | 1 | P2-13 字段覆盖不完整 |
| **合计** | **3** | **16** | **14** | |

---

## 测试覆盖度评估

| 被测模块 | 测试文件 | 覆盖状态 | 缺失覆盖 |
|----------|----------|----------|----------|
| `github_api.py` | `test_github_api.py` | 部分 | `fetch_all` 并发分页逻辑、`get_readme` 缓存逻辑、`get_user_repos` 分页未测试 |
| `http_client.py` | `test_http_client.py` | 部分 | 重试逻辑（retries > 0）、超时处理、429 状态码重试、异常返回 (-1) 场景 |
| `models.py` | `test_models.py` | 良好 | `from_github_api` 的边界（超大 stars、特殊字符）、`to_dict` 的完整字段验证 |
| `database.py` | `test_database.py` | 良好 | 并发写入场景（lock 机制）、大文件加载性能 |
| `repositories/` | `test_repositories.py`, `test_sqlite_backend.py` | 良好 | `JSONAIRepository` 的 `delete` 和 `save` 未充分测试、SQLite `close()` 后操作异常处理 |
| `rule_classifier.py` | `test_classifiers.py` | 部分 | `_load_learned_overrides` 文件系统交互、`_load_auto_ecologies`、边界容错（缺失字段） |
| `engine.py` | `test_engine.py` | 良好 | `_process_single` 的异常路径（`KeyError` 在 `item['owner']['login']`）、`_classify_item` 的 `existing` 参数分支 |
| `report.py` | `test_integration.py`, `test_classifier.py` | 部分 | `_build_html` 的 weekly_data 各 tab 渲染、`_feedback_url` 生成、大数量 items 性能 |
| `lists_manager.py` | `test_lists_manager.py` | 良好 | `get_lists_summary` 的异常处理（`get_list_items` 失败）、`migrate_lists_to_db` 的大列表性能 |
| `notify.py` | `test_notify.py` | 良好 | `EmailNotifier.send` 的异常路径（SMTP 连接失败）、`Notifier.send` 的多通道异常隔离 |
| `notion.py` | `test_notion.py` | 部分 | `_clear_database` 的异常处理、`_build_properties` 的 `rich_text`/`url` 类型 |
| `release_tracker.py` | `test_trackers.py`, `test_integration.py` | 良好 | `digest_with_llm` 的 LLM 调用、并发异常处理、`_is_within_window` 的边界时间 |
| `fork_tracker.py` | `test_trackers.py` | 部分 | `get_user_forks` 的 API 错误处理、`check` 的并发异常 |
| `import_helper.py` | `test_import_helper.py` | 良好 | `import_from_csv` 的编码异常、空文件处理 |
| `correct_command.py` | `test_correct_command.py` | 部分 | `_save()` 中 `generate_learned_overrides` 的触发条件（min_count=2）、反馈内容验证 |
| `feedback_loop.py` | `test_feedback_loop.py` | 良好 | `generate_learned_overrides` 的完整规则生成逻辑、`scan_manual_overrides` 的 `last_entry` 分支 |
| `new_pipeline.py` | `test_new_pipeline.py` | 部分 | `enrich` 阶段、`classify` 阶段、`sync_notion` 阶段、`track_releases` 阶段、`track_forks` 阶段均跳过未测 |
| `classifier.py` (CLI) | `test_classifier.py` | 良好 | `_parse_args` 的完整参数解析、环境变量预设的边界格式 |

---

## 总体评价

### 优点
1. **测试结构清晰**：按模块划分测试文件，命名规范统一
2. **Mock 使用得当**：大部分测试正确使用 `unittest.mock` 隔离外部依赖
3. **集成测试充分**：`test_integration.py` 验证了 StarItem、StarsDB、ReportGenerator、ReleaseTracker 的真实交互
4. **版本控制测试完善**：`test_feedback_loop.py` 对规则版本变更的场景覆盖全面
5. **Pipeline 架构测试**：`test_new_pipeline.py` 验证了 StageRegistry 的依赖检查、循环依赖检测等核心机制

### 主要风险
1. **P0-1 mock 路径错误**：`config.LOCKED_ECOLOGIES` 的 patch 路径可能导致测试在真实配置变化时失败
2. **P0-2 / P0-3 资源泄漏**：临时文件和目录清理不当可能导致 CI 不稳定
3. **P1-8 时间依赖**：`test_check_all_baseline_first_discovery` 使用 `datetime.now()` 作为 `first_seen`，7 天后将变为 flaky test
4. **MockDB 与真实 DB 行为不一致**：多处使用简化 MockDB，可能掩盖真实集成问题
