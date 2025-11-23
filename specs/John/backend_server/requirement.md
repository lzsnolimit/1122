# 需求文档（草案）
## 引言
本需求针对 README 中第 6 条：「写一个 server 能返回 data.db 里最新的投资建议」，并聚焦与前端对接的接口定义与验收标准。

## 需求
### 需求 6 – 最新投资建议服务接口
**用户故事：** 作为前端开发者，我需要一个可用的 HTTP 接口来获取最近的投资建议数据，以便在页面中展示。

#### 接口定义
- 接口地址：`GET http://127.0.0.1:8000/api/get_last_10_advises`
- 鉴权：无需（本地开发阶段）。
- CORS：允许浏览器前端访问（至少启用 GET 的跨域响应）。

#### 响应数据
- 成功返回：`200 OK`，JSON 数组（长度最多 10），每个元素为一个投资建议对象，至少包含以下字段：
  - `symbol`：字符串，代币符号（如 `BTC`、`ETH`）。
  - `advice_action`：字符串，投资动作建议（如 `buy`、`hold`、`sell`）。
  - `reason`：字符串，简要原因说明。
  - `advice_strength`：字符串，建议强度，取值为以下三档之一：
    - `high`：强烈建议按 `advice_action` 执行（信号强、置信度高）。
    - `medium`：建议但需关注风险与波动（信号中等、置信度中）。
    - `low`：谨慎对待（信号弱或不确定、置信度低）。
  - `predicted_at`：数字，预测时间（UNIX Epoch 秒级时间戳，例如 `1732286100`）。
  - `kline_24h`：对象或 `null`（可选，若实现），最近 24 小时的 K 线数据快照；若暂未实现可返回空或省略。
- 空数据返回：`200 OK`，返回空数组 `[]`。
- 错误返回：
  - `500 Internal Server Error`：服务内部错误，返回 `{ "error": "internal_error", "message": "..." }`。

#### 接受标准（EARS）
1. 当客户端请求 `GET /api/get_last_10_advises` 时，系统应返回最近的最多 10 条投资建议（按预测时间 `predicted_at` 倒序，最近在前）。
2. 当存在不足 10 条建议时，系统应返回实际可用条数（不少于 0 条）。
3. 当数据库 `data.db` 无任何建议时，系统应返回空数组并状态码为 `200`。
4. 当发生服务器内部异常时，系统应返回状态码 `500` 与错误信息 JSON（不暴露敏感堆栈）。
5. 当 24 小时 K 线数据已实现时，系统应在每条建议对象中包含 `kline_24h` 字段；当尚未实现或数据缺失时，系统应允许该字段为 `null` 或省略。
6. 每条建议对象必须包含 `predicted_at` 字段，类型为整数的 UNIX 秒级时间戳。
7. 每条建议对象必须包含 `advice_strength` 字段，且取值仅可为 `high`、`medium`、`low` 之一。
8. 当 `predicted_at` 相同或缺失时，系统应以插入时间或主键倒序作为次级排序，保证结果稳定。
9. 当浏览器前端发起跨域 GET 请求时，系统应返回允许的 CORS 头以保证可访问性。

#### 业务约束与约定
- 前端追踪的固定代币集合（由 README 定义）：
  - `USDT`, `BTC`, `ETH`, `USDC`, `SOL`, `XRP`, `ZEC`, `BNB`, `DOGE`
- 数据来源：`data.db`（SQLite），由上游 LLM 与工具链生成并持久化投资建议。
- 排序规则：按 `predicted_at` 数值倒序返回（最近在前；若相同则按插入时间/主键倒序）。

#### 示例响应（200 OK）
```json
[
  {
    "symbol": "BTC",
    "advice_action": "buy",
    "reason": "Momentum strong; derivatives funding neutral; positive dev activity",
    "advice_strength": "high",
    "predicted_at": 1732286100,
    "kline_24h": null
  },
  {
    "symbol": "ETH",
    "advice_action": "hold",
    "reason": "Mixed on-chain flows; sentiment improving",
    "advice_strength": "medium",
    "predicted_at": 1732283700,
    "kline_24h": null
  }
]
```

---
请确认上述接口与验收标准是否满足第 6 条需求；确认后我将继续在设计与任务拆解中沿用本规范。
