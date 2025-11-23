我们是一个AI分析虚拟货币预测价格的应用，我们核心的思路是

1: 监控x和reddit上的KOL发言，采集下来存进文件，包含时间和发言人，发言内容，以及发言人简单介绍。
2: 调用LLM分析最需要attention的symbol(get_tracking_cryptocurrenc函数返回的)，和详细的需要attention的原因。返回一个json。同时调用save_tracking_symbols_to_resources抓取这些symbol
3: 我们有一个工具集，工具集包含很多分析预测股价的函数，每个函数都有预期的输入和输出，把上一步我们获得的数据集，和json feed给code agent，让code agent生成一段代码综合的分析这个symbol。返回关键节点的structure 数据
4：LLM summary函数，也是tool，告诉code agent生成所有的structue数据，和所有的context，给llm让llm给出投资意见。投资意见存进 sqlite data.db。
5: 运行code
6: 写一个server 能返回data.db里最新的投资建议

