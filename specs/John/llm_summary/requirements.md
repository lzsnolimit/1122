# 需求文档（草案）
## 引言
本需求针对 README 中第 4 条（“LLM summary 函数”）：作为一个工具函数，输入目标代币 `symbol` 与所有分析预测股价函数的综合结果（字符串），在结合 `CODE_GEN/resources/social_media_analysis.txt` 以及 `CODE_GEN/resources/{symbol}.txt` 的上下文后，使用 `langchain-openai` 调用 `gpt-5`（medium reasoning effort）生成投资建议，并将结果写入本地 SQLite `data.db` 的 `advises` 表，供服务端接口 `/api/get_last_10_advises` 返回。

## 需求
### 需求 4 – LLM Summary 工具函数
**用户故事：** 作为策略生成链路的开发者，我需要一个工具函数能把社媒分析、目标代币的 24h 数据与代码代理的综合分析结果喂给 LLM，让其输出结构化的投资建议，并持久化到数据库，便于前端与后端统一使用。

#### 函数接口
- 名称：`llm_summary`
- 入参：
  - `symbol`：字符串。目标代币符号（如 `BTC`、`ETH`、`SOL`）。
  - `analysis_results`：字符串。所有分析预测股价函数的综合结果集（代码代理生成的结构化摘要或说明，以字符串形式传入）。
- 行为：读取并整合以下上下文，调用 LLM 生成建议并入库：
  1. `CODE_GEN/resources/social_media_analysis.txt`（社媒/KOL 分析 JSON 或文本）。
  2. `CODE_GEN/resources/{symbol}.txt`（由 `save_tracking_symbols_to_resources` 生成的该代币近 24h 数据的 JSON）。
  3. 传入的 `analysis_results`（所有分析工具的输出汇总）。
- 输出：无直接返回值；将建议写入 `data.db` → `advises` 表。

#### LLM 配置
- 库：`langchain-openai`
- 模型：`gpt-5`
- 推理强度：`medium reasoning effort`
- 其他建议：
  - `temperature` 建议设置为中低（如 `0.2~0.5`）以提高一致性。
  - 通过结构化输出（JSON 模板或模式约束）保证字段合法、可解析。

#### 数据库写入字段（与服务端 API 契约一致）
- `symbol`：字符串（如 `BTC`、`ETH`）。
- `advice_action`：字符串，建议操作，枚举：`buy` | `hold` | `sell`。
- `advice_strength`：字符串，建议强度，枚举：`high` | `medium` | `low`。
- `reason`：字符串，建议的简要理由说明。
- `predicted_at`：整数，UNIX Epoch 秒级时间戳（建议以生成时刻 `now()` 写入）。
- `price`：数字，最新价格（建议取 `{symbol}.txt` 中最新 K 线的 `close` 或 `stats.close_latest`，单位与资源文件一致，如 `USD`）。
- `kline_24h`：可选字段（若后续实现），最近 24 小时 K 线数据快照；当前可不写入或置空。

#### 接受标准（EARS）
1. 当存在 `CODE_GEN/resources/{symbol}.txt` 与 `CODE_GEN/resources/social_media_analysis.txt` 时，当调用 `llm_summary(symbol, analysis_results)`，系统应读取两者并合并 `analysis_results` 为完整上下文，提供给 LLM。
2. 当 LLM 返回结构化建议时，系统应解析并校验字段，确保 `advice_action ∈ {buy, hold, sell}`、`advice_strength ∈ {high, medium, low}`、`predicted_at` 为整数秒时间戳，`symbol` 与入参一致。
3. 当可从 `{symbol}.txt` 提取最新价格时，系统应写入 `price` 字段；若数据缺失则允许跳过并记录日志。
4. 当解析通过时，系统应将建议插入 `data.db` 的 `advises` 表，使其可被 `server.py` 的接口 `GET /api/get_last_10_advises` 查询并返回。
5. 当 `social_media_analysis.txt` 或 `{symbol}.txt` 不存在或不可读时，系统应记录错误并进行降级处理（例如仅使用可用的上下文与 `analysis_results`），但不得写入不完整或非法字段的建议。
6. 当 LLM 响应不可解析或字段不合法时，系统应拒绝入库并记录原因（日志），避免脏数据进入 `advises` 表。
7. 当数据库写入成功时，系统应保证排序字段 `predicted_at` 为当前生成时刻的 UNIX 秒级时间戳，以便接口按倒序返回最新建议。
8. 当重复调用 `llm_summary` 生成同一 `symbol` 的建议时，系统应按最新生成的时间入库；是否去重由上游策略控制（本函数不强制去重）。
9. 当发生 LLM 超时或网络错误时，系统应返回错误并记录日志，不得产生半成品入库。

#### 业务约束与约定
- 追踪代币集合：`USDT`, `BTC`, `ETH`, `USDC`, `SOL`, `XRP`, `ZEC`, `BNB`, `DOGE`（参考 README）。
- 资源约定：`CODE_GEN/resources/{symbol}.txt` 内容为 JSON 文本，由 `save_tracking_symbols_to_resources` 生成（包含 24h bars、stats 等）。
- 社媒分析：`CODE_GEN/resources/social_media_analysis.txt` 为上游第 2 步生成的 JSON/文本，包含需要关注的 `symbol` 与原因。
- 数据库文件：`data.db`，表名 `advises`；字段结构遵循服务端数据契约（详见 `service/db_service.py`）。
- 安全与合规：本地开发阶段无需鉴权；生产需加入密钥或访问控制（后续设计另行补充）。

#### 示例（概念）
- 输入：
  - `symbol = "BTC"`
  - `analysis_results = "{...全部分析工具的结构化汇总...}"`
  - `CODE_GEN/resources/social_media_analysis.txt = "{...社媒/KOL 分析...}"`
  - `CODE_GEN/resources/BTC.txt = "{...BTC 24h 数据 JSON...}"`
- 期望写入：
  ```json
  {
    "symbol": "BTC",
    "advice_action": "buy",
    "advice_strength": "high",
    "reason": "社媒情绪积极且链上资金流入增加，技术指标共振",
    "predicted_at": 1732286100
    ,"price": 68432.15
  }
  ```

---
请确认上述需求（草案）是否满足“LLM summary 函数”的预期；确认后我将依据该需求编写技术设计与任务拆解。
