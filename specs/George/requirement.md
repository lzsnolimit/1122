data_source 30分钟级的数据

trading_data_source	
价格 (Price)：开盘价 (Open)、最高价 (High)、最低价 (Low)、收盘价 (Close)
成交量 (Volume)：该时间窗口的总成交量

blockchain_data_source	
未花费交易产出 (UTXOs)，区块高度，区块时间
交易笔数（Transition Count），交易金额，平均交易费（Gas Fee）
网址活跃数（Active Adress）新增地址数
巨鲸钱包余额
（能找到多少就找到多少，不行就mock）

development_data_source	（我这边直接mock）
开发指标: 核心开发者提交数的 7 日平均增长率	
代码提交记录 (Commit Logs)：包括提交时间 (Timestamp)
贡献者 ID/用户名 (Contributor ID)：用于识别核心开发者
代码更新频率/行数变化 (Code Change)：量化每次提交的规模/重要性

对于sentiment处理的insight 情绪的评分可以作为止损/止盈的依据