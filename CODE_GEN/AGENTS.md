# Codex CLI Agents Task – 生成 main.py 并调用分析函数与 llm_summary

本文件为仓库范围的代理说明，指导代理生成符合需求的代码。请严格按下述步骤执行，做到“只做被要求的事”。

重要说明：social_media_analysis.txt 中的 symbol 只有一个；生成的代码仅需处理该单一 symbol，不为多符号设计循环或并发。

## 背景资源文件
- 读取 `resources/social_media_analysis.txt`（最近十分钟的社媒分析，含 symbol 与语义分析）中的symbol和reason。
- 读取 `resources/` 目录下{{symbol}} 的最近 24 小时数据 `{{symbol}}.txt`。
- 阅读并调用 `function_list.py` 中你认为必要的函数，将“调用了哪些函数 + 返回结果”拼接为一个 `summary` 字符串。
- 最后调用 `final_analysis.llm_summary(symbol, analysis_results=summary)`。
- 将生成的代码保存到当前目录 `main.py`。

## 实施步骤（建议按序执行）
- 代码生成（写入 `main.py`）：
  - 导入：`from development_process import dev_data_analysis`
`from onchain_process import chain_data_analysis`
`from technical_metrics_builder import market_data_analysis`
  - 对 social_media_analysis.txt 你读取到的单一 symbol：
    - 调用上述需要的函数，获取返回值；允许返回 `None`。
    - 将“函数介绍: 返回结果（字符串化）”拼接为单行或多行的 `summary`，例如：`market_data_analysis: None; dev_data_analysis: None; chain_data_analysis: None`。
    - 调用 `from final_analysis import llm_summary` 并执行：`llm_summary(symbol=symbol, analysis_results=summary)`。
  - 仅处理一个 symbol，不进行列表循环或并发。
  - 添加最小化的错误处理：失败被捕获并记录；打印简洁日志。
  - 你可以读取social_media_analysis的数据作为生成代码的依据，但是不需要在代码中读取这个文件。
  - 最小化生成代码，不要过度fallback
- 验证运行：
  - 执行 `python main.py`；至少调用一次 `llm_summary`。
  - 你唯一能修改的就是main.py 不要修改任何其他文件。
  

## 接受标准
- `main.py` 文件已创建，Python 3.10+，遵循 PEP8，使用类型注解；代码与字符串均为英文。
- 程序能：
  - 构造包含“函数名与返回结果”的 `summary` 并传入 `llm_summary`；
  - 对返回 `None` 的函数也要在 `summary` 中明确体现（如 `None`）。
  - 仅处理单一 symbol，不存在多符号循环或并发逻辑。
- 只新增main.py；遵循仓库既有结构与风格。

## 代码约束与风格
- 仅创建 `main.py`（用户已明确要求）；其余文件非必要不改动。
- 导入路径使用相对/包内导入；不依赖网络除 `llm_summary`。
- 错误处理简洁：文件缺失、JSON 解析失败、函数调用异常均要被捕获。
- 日志/打印保持简洁（英文）。


## 代理工作提示
- 在执行工具命令前给出简短前言；对多步相关操作进行分组说明。
- 优先编辑现有文件；仅在必要时创建新文件（本任务仅 `main.py`）。
