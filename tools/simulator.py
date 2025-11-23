# simulator.py
import json
import os
import random
import uuid
from datetime import datetime, timedelta

# 定义我们要模拟的代币符号
TARGET_SYMBOLS = ["USDT","BTC","ETH","USDC","SOL","XRP","ZEC","BNB","DOGE"]

def generate_scraped_data(symbol):
    """
    模拟从 GitHub/GitLab 爬取的过去 24 小时的原始开发活动数据。
    数据粒度为 30 分钟。
    """
    now = datetime.utcnow()
    # 调整时间到最近的 30 分钟整点
    now = now.replace(minute=30 if now.minute >= 30 else 0, second=0, microsecond=0)
    
    raw_data_entries = []
    
    # 生成过去 24 小时的数据 (24 * 2 = 48 个数据点)
    for i in range(48):
        time_point = now - timedelta(minutes=30 * i)
        timestamp_str = time_point.isoformat() + "Z"
        
        # 模拟基础提交数 (随机波动)
        # BTC/ETH 通常较高，其他较低
        base_activity = random.randint(0, 15) if symbol in ["BTC", "ETH"] else random.randint(0, 5)
        
        # 偶尔的爆发 (Merge Request 合并)
        if random.random() > 0.9:
            base_activity += random.randint(10, 30)
            
        # 模拟核心开发者比例 (通常是总提交的一小部分)
        core_dev_count = int(base_activity * random.uniform(0.2, 0.6))
        
        # 构建类似 API 响应的单条记录
        entry = {
            "collected_at": timestamp_str,
            "repo_stats": {
                "total_commits": base_activity,
                "core_contributors_commits": core_dev_count,
                # 添加一些"噪音"数据，使其看起来像原始爬虫数据
                "active_repos": random.randint(1, 5),
                "unique_authors": max(1, int(base_activity / 2)) if base_activity > 0 else 0,
                "latest_commit_hash": str(uuid.uuid4())[:8] if base_activity > 0 else None
            }
        }
        raw_data_entries.append(entry)
    
    # 按时间正序排列 (旧 -> 新)
    raw_data_entries.reverse()
    
    # 构建最终的 JSON 结构
    final_json = {
        "symbol": symbol,
        "source": "github_scraper_v2",
        "meta": {
            "scraped_timestamp": datetime.utcnow().isoformat(),
            "period": "24h",
            "granularity": "30min"
        },
        "activity_log": raw_data_entries
    }
    
    return final_json

def save_raw_file(symbol, data):
    # 1. 构建路径
    # 使用 os.path.abspath 确保路径解析正确
    base_dir = os.path.abspath(os.path.join("..", "CODE_GEN", "developer"))
    
    if not os.path.exists(base_dir):
        print(f"Creating directory: {base_dir}")
        os.makedirs(base_dir)
        
    file_path = os.path.join(base_dir, f"{symbol}.txt")
    
    # 2. 写入 JSON
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
        
    print(f"✅ [Scraper Mock] Saved raw data for {symbol} to {file_path}")

if __name__ == "__main__":
    print("--- Starting Mock Scraper (Last 24h) ---")
    for sym in TARGET_SYMBOLS:
        raw_json = generate_scraped_data(sym)
        save_raw_file(sym, raw_json)