# development_process.py

import pandas as pd
import numpy as np
import json
import os

# --- 1. Your Metric Calculation Function ---

def calculate_development_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates metrics based on project development activity.
    Input: 'Commit_Count', 'Core_Dev_Commits'
    """
    df = df.copy()

    # 1. Core Developer Commit Moving Average (7 days = 336 periods)
    # Note: With only 24h of data, this will likely be NaN. 
    # We use min_periods=1 to force a calculation for demo purposes, 
    # but in production, strictly adhere to window size.
    df['Core_Dev_MA_7D'] = df['Core_Dev_Commits'].rolling(window=336, min_periods=1).mean()
    
    # 2. Core Developer Activity Signal
    df['Dev_Activity_Signal'] = df['Core_Dev_Commits'] / df['Core_Dev_MA_7D'].replace(0, np.nan)
    
    # 3. Total Commits Accumulation (3 days = 144 periods)
    df['Total_Commits_Acc_144'] = df['Commit_Count'].rolling(window=144, min_periods=1).sum()

    return df

# --- 2. Loader & Parser ---

def load_raw_dev_data(symbol):
    """
    读取 ../CODE_GEN/developer/{symbol}.txt 并解析为标准 DataFrame
    """
    file_path = os.path.join("..", "CODE_GEN", "developer", f"{symbol}.txt")
    
    if not os.path.exists(file_path):
        print(f"Error: File not found for {symbol}")
        return pd.DataFrame()
        
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_json = json.load(f)
        
    # 解析嵌套的 JSON 结构 (activity_log -> repo_stats)
    logs = raw_json.get("activity_log", [])
    if not logs:
        return pd.DataFrame()
        
    # 提取需要的数据并重命名以匹配 calculate_development_metrics 的输入要求
    data_list = []
    for entry in logs:
        stats = entry.get("repo_stats", {})
        data_list.append({
            "timestamp": entry.get("collected_at"),
            "Commit_Count": stats.get("total_commits", 0),        # 映射到您的函数输入名
            "Core_Dev_Commits": stats.get("core_contributors_commits", 0) # 映射到您的函数输入名
        })
        
    df = pd.DataFrame(data_list)
    
    # 处理时间戳
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    return df