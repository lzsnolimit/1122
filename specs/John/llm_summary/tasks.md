# 实施计划（LLM Summary）

- [ ] 1. 依赖与环境准备
  - 在 `requirements.txt` 增加 `langchain-openai`（以及必要的 `openai` 依赖，视版本而定）。
  - 在部署环境配置：`OPENAI_API_KEY` 与 `AZURE_GPT_ENDPOINT`（供 ChatOpenAI 作为端点使用）。
  - _Requirement: 需求 4 – LLM Summary 工具函数_

- [ ] 2. 数据库安全迁移（新增 `price` 字段）
  - 检查 `data.db` 中 `advises` 表结构是否存在 `price` 字段（`PRAGMA table_info(advises)`）。
  - 若不存在，执行 `ALTER TABLE advises ADD COLUMN price REAL`（幂等处理）。
  - 更新 `service/db_service.py` 查询逻辑（已支持检测并返回 `price`，如需补充单元验证则新增）。
  - _Requirement: 与服务端数据契约一致；返回含 `price`_

- [ ] 3. 读取上下文与价格提取
  - 读取 `CODE_GEN/resources/social_media_analysis.txt`（兼容 JSON/文本）。
  - 读取 `CODE_GEN/resources/{symbol}.txt` 并解析 JSON：
    - 优先使用 `stats.close_latest` 作为最新价格；
    - 兜底使用 `bars` 最后一项的 `close`；
    - 单位与资源一致（通常 `USD/USDT`）。
  - 整理 `analysis_results`（字符串），形成完整上下文摘要供 LLM 使用。
  - _Requirement: reason 必须中文；含 price 字段_

- [ ] 4. 设计并实现 LLM 调用（langchain-openai）
  - 使用 `ChatOpenAI(model="gpt-5", base_url=os.getenv("AZURE_GPT_ENDPOINT"))`，默认温度，不显式设置。
  - 若 SDK 支持，设置 `reasoning={"effort": "medium"}`；若不支持，则在系统提示中声明“需要中等推理力度”。
  - System 提示明确输出为 JSON 且字段包含：`symbol, advice_action, advice_strength, reason(中文), predicted_at(UNIX秒), price`。
  - User 提示包含：symbol、社媒分析摘要、资源摘要（指标与价格）、analysis_results。
  - _Requirement: 使用 gpt-5；medium reasoning；reason 中文_

- [ ] 5. 结构化解析与字段校验
  - 使用结构化解析器或严格 `json.loads` + 手动校验：
    - `advice_action ∈ {buy, hold, sell}`；
    - `advice_strength ∈ {high, medium, low}`；
    - `reason` 必须为中文（可通过简单中文字符检测或提示约束保证）；
    - `predicted_at` 为 UNIX 秒（若模型未给出则以 `int(time.time())` 兜底）；
    - `symbol` 与入参一致；
    - `price` 为数字且与提取的价格合理一致（允许模型与输入提取值一致或以输入值为准）。
  - 校验失败：拒绝入库并记录日志。
  - _Requirement: 数据契约与服务端一致_

- [ ] 6. 入库写入（SQLite）
  - `INSERT INTO advises (symbol, advice_action, advice_strength, reason, predicted_at, price) VALUES (?,?,?,?,?,?)`。
  - 写入成功后记录操作日志（symbol、predicted_at）。
  - _Requirement: 服务端接口可读到包含 price 的建议_

- [ ] 7. 接口联调与验证
  - 启动 `server.py`，访问 `GET /api/get_last_10_advises`，确认：
    - 返回对象包含 `symbol, advice_action, advice_strength, reason(中文), predicted_at, price`；
    - 排序按 `predicted_at DESC`；
    - 当存在旧记录也能正确返回最新建议在前。
  - _Requirement: 后端返回字段满足前端需求_

- [ ] 8. 错误处理与降级策略
  - 资源文件缺失：使用可用上下文并提示原因，不写入不完整/不合法建议。
  - LLM 返回不可解析：重试 1 次（可选）；失败则记录并退出，不入库。
  - LLM 网络或限流：记录错误并退出，不产生半成品数据。
  - _Requirement: 健壮性保障_

- [ ] 9. 测试与质量保障
  - 单元测试（可选）：价格提取、枚举校验、中文 reason 检查、DB 写入路径。
  - 集成测试：伪造资源文件与 analysis_results，模拟 LLM 输出，端到端验证接口返回。
  - _Requirement: 满足验收标准_

- [ ] 10. 文档与运维
  - 在设计与需求文档中标注最终字段与端点环境变量要求（已更新）。
  - 记录运行说明：设置 `OPENAI_API_KEY` 与 `AZURE_GPT_ENDPOINT`，执行生成函数后通过接口查看。
  - _Requirement: 可操作性与可维护性_

---
**完成判定（DoD）**
- 通过 LLM 生成的建议已成功写入 `advises`，包含 `price` 与中文 `reason`；
- `GET /api/get_last_10_advises` 返回结构正确且含最新建议；
- 异常路径处理合理，日志清晰，无脏数据入库。

