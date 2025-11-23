data_source 30分钟级的数据

trading_data_source	
价格 (Price)：开盘价 (Open)、最高价 (High)、最低价 (Low)、收盘价 (Close)
成交量 (Volume)：该时间窗口的总成交量
衍生品指标: 资金费率的平均值、标准差、斜率	trading_data_source	
资金费率 (Funding Rate)：该时间窗口内的实时或聚合资金费率快照
未平仓合约量 (Open Interest, OI)：该时间窗口末的 OI 快照

blockchain_data_source	
已花费交易产出 (UTXOs) 的实现价格 (Realized Price/Value)：用于计算 SOPR 和 MVRV 的分母 (Realized Cap)
交易时间 (Timestamp)：精确到秒
trading_data_source	市场价格 (Market Price/Cap)：用于计算 MVRV 的分子 (Market Cap)
流量: 交易所流入/流出净额	交易哈希 (Tx Hash), 发送/接收钱包地址：用于识别交易所的已知钱包地址（热钱包/冷钱包）
交易金额 (Amount)：追踪资金进出交易所钱包的净变化
流量: 非零地址数增长率	
唯一钱包地址总数 (Total Unique Addresses)：按小时快照或每日增量

social_data_source	
帖子/评论内容 (Content/Text)：用于 NLP 计算原始情绪分数
发布时间 (Post Timestamp)：精确到秒/分钟
互动数据 (Engagement)：点赞/评论/转发数（作为权重因子）

development_data_source	
开发指标: 核心开发者提交数的 7 日平均增长率	
代码提交记录 (Commit Logs)：包括提交时间 (Timestamp)
贡献者 ID/用户名 (Contributor ID)：用于识别核心开发者
代码更新频率/行数变化 (Code Change)：量化每次提交的规模/重要性