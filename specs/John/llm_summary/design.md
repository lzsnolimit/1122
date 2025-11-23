# 技术设计（LLM Summary）

## 概述
LLM Summary 是一个工具函数，负责聚合多源上下文（社媒分析、目标代币近 24 小时数据、所有分析预测股价的函数输出），调用 `langchain-openai` 的 `gpt-5` 模型（推理强度设为 `medium`），生成结构化投资建议，并持久化到 SQLite `data.db` 的 `advises` 表。该建议随后由后端接口 `GET /api/get_last_10_advises` 提供给前端。

```mermaid
flowchart LR
    SM[social_media_analysis.txt] --> C[LLM Summary]
    RS[CODE_GEN/resources/{symbol}.txt] --> C
    AR[analysis_results (string)] --> C
    C -->|validated JSON| DB[(SQLite data.db: advises)]
    FE[Frontend] -->|GET /api/get_last_10_advises| S[server.py]
    S --> DB
```

## 技术栈与选择
- 语言与运行时：Python 3.12
- LLM 调用：`langchain-openai`（聊天模型），`gpt-5`
- 推理强度：medium（在模型参数中设置 reasoning effort；若 SDK 不支持该字段则通过系统提示降级控制）
- 结构化输出：LangChain 的结构化输出解析（`JsonOutputParser` 或 `Pydantic` 模式）
- 持久化存储：SQLite `data.db`
- 配置与密钥：通过环境变量：
  - `OPENAI_API_KEY`（必需）
  - `AZURE_GPT_ENDPOINT`（必需，用作 ChatOpenAI 的 `base_url`/`openai_api_base`）

## 输入与数据源
- `social_media_analysis.txt`（路径：`CODE_GEN/resources/social_media_analysis.txt`）
  - 可能为 JSON 或自由文本；需要兼容解析为结构化对象或作为纯文本上下文。
- `{symbol}.txt`（路径：`CODE_GEN/resources/{symbol}.txt`）
  - 由 `save_tracking_symbols_to_resources` 生成，格式为 JSON，包含：
    - `bars`: 数组，每项包含 `timestamp, open, high, low, close, volume` 及可选指标
    - `stats`: 对象，建议优先使用 `stats.close_latest` 作为最新价格来源
- `analysis_results`（string）
  - 由代码代理整合所有分析预测股价函数的汇总结果，可能包含多维信号、权重或解释

## 字段与数据契约
- 输出建议必须包含：
  - `symbol`（string）：与入参一致
  - `advice_action`（string）：`buy` | `hold` | `sell`
  - `advice_strength`（string）：`high` | `medium` | `low`
  - `reason`（string，中文）：简洁明确的中文理由说明
  - `predicted_at`（int）：UNIX 秒级时间戳（生成时刻）
  - `price`（number）：最新价格（优先 `stats.close_latest`；若缺失，则取最后一个 `bar.close`）

> 说明：不再需要返回 `kline_24h`；后端与前端均不依赖该字段。

## 价格提取策略
- 首选：`resources_{symbol}.stats.close_latest`
- 兜底：`resources_{symbol}.bars[-1].close`（若存在）
- 单位：与资源文件一致（通常为 `USD` 或 `USDT`）；设计中保留数值，不在此函数中做单位转换
- 异常：若无法获取价格，允许跳过 `price` 并记录日志，但验收建议尽量补齐（便于前端展示）

## LLM 交互设计
- 模型：`gpt-5`
- 推理：`medium`
- 温度：默认（不显式设置）
- 输出约束：严格 JSON（带枚举与类型约束）

提示模板（概念）：
- System（中文，约束输出与语言）：
  - 明确输出为 JSON，字段与枚举约束
  - 要求 `reason` 使用中文表达，简洁且可读
- User（上下文与任务）：
  - 提供 `symbol`、社媒分析文本/JSON、`{symbol}.txt` 摘要（价格、变化、关键指标）以及 `analysis_results`
  - 要求模型综合分析并给出建议

示例伪代码（仅设计说明，代码使用英文标识）：
```python
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import SystemMessage, HumanMessage
import os

model = ChatOpenAI(
    model="gpt-5",
    # 如果 SDK 支持，可设置：reasoning={"effort": "medium"},
    # 将 Azure 端点从环境变量注入；参数名称依 SDK 版本可能为 base_url 或 openai_api_base：
    base_url=os.environ.get("AZURE_GPT_ENDPOINT")
)

system = SystemMessage(content=(
    "你是加密资产投资顾问。必须以 JSON 输出，字段为："
    "symbol(advice symbol), advice_action(buy|hold|sell), advice_strength(high|medium|low),"
    "reason(中文), predicted_at(UNIX秒), price(number)。"
))

human = HumanMessage(content=(
    f"symbol: {symbol}\n" 
    f"social_media_analysis: {social_media_text_or_json}\n"
    f"symbol_24h_resource_summary: {symbol_resource_summary}\n"
    f"analysis_results: {analysis_results}\n"
    "请综合以上信息，输出上述 JSON 字段，reason 必须为中文。"
))

resp = model([system, human])
parsed = json.loads(resp.content)  # 加强健壮性：结构校验与枚举校验
```

> 注：实际实现建议使用 LangChain 的结构化输出解析器，避免手工 `json.loads()` 的脆弱性。

## 数据库与迁移
- 表：`advises`
  - 现有字段：`id, symbol, advice_action, advice_strength, reason, predicted_at, created_at`
  - 新增字段：`price REAL`
- 迁移策略：
  - 启动/首次写入前执行一次安全迁移：
    - 检查 `PRAGMA table_info(advises)` 是否含 `price`
    - 若无，则执行：`ALTER TABLE advises ADD COLUMN price REAL`
- 写入语句（示意）：
  - `INSERT INTO advises (symbol, advice_action, advice_strength, reason, predicted_at, price) VALUES (?,?,?,?,?,?);`

## 服务端接口适配
- 路由：`GET /api/get_last_10_advises`
- 数据：后端从 `db_service.get_last_10_advises()` 读取；当表包含 `price` 字段时，JSON 中包含 `price`
- 排序：按 `predicted_at DESC, rowid DESC` 保持稳定

## 错误处理与健壮性
- 文件读取失败：记录日志并回退到可用上下文；不得写入不合法建议
- JSON 解析失败：模型提示降级或重试（可设定最多 1~2 次），仍失败则拒绝入库
- 字段校验失败：枚举/类型不合法直接拒绝入库并记录原因
- LLM 网络或限流：捕获异常，记录日志，不产生半成品数据

## 安全与合规
- 密钥管理：`OPENAI_API_KEY` 仅通过环境变量传入，不写入代码与仓库
- 请求安全：关闭不必要日志的原始上下文内容，避免泄露敏感数据
- CORS：服务端仅在开发环境开放 `*`；生产收敛到受信域名

## 测试策略
- 单元测试：
  - 结构化解析器：对合法与非法响应进行字段校验
  - 价格提取：对 `stats.close_latest` 与 `bars[-1].close` 的选择与兜底逻辑
  - 迁移：模拟缺少 `price` 列的表，验证 `ALTER TABLE` 执行与幂等性
- 集成测试：
  - 伪造 `social_media_analysis.txt` 与 `{symbol}.txt`，模拟 LLM 响应，写入 SQLite 后通过接口读取验证包含 `price` 与中文 `reason`

## 性能与扩展
- 调用频率：控制调用次数（例如按 symbol 去重与时间窗口），避免重复生成建议
- 缓存：可选在资源摘要层进行轻量缓存；LLM 调用不建议缓存以避免过时建议
- 扩展：后续可加入风险分级、上下文权重、更多分析信号（不影响当前字段契约）

## 任务落地规划（简要）
1. 增加 `price` 列的安全迁移工具（`service/db_service.py` 或新建 `service/migrations.py`）
2. 实现 `llm_summary(symbol, analysis_results)`：读取上下文 → LLM 调用 → 字段校验 → 入库
3. 验证 `GET /api/get_last_10_advises` 返回含 `price` 且 `reason` 为中文
4. 编写基础测试与异常路径验证

---
请确认上述设计是否满足你的预期（特别是 `langchain-openai` 的调用方式与 `gpt-5` + medium 推理强度的配置）。确认后我将继续进行任务拆解与实现。
