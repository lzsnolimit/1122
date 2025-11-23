# simulator.py
import json
import os
import random
import uuid
from datetime import datetime, timedelta

# Define the token symbols we want to simulate
TARGET_SYMBOLS = ["USDT", "BTC", "ETH", "USDC", "SOL", "XRP", "ZEC", "BNB", "DOGE"]

def generate_scraped_data(symbol):
    """
    Simulates raw development activity data scraped from GitHub/GitLab for the past 24 hours.
    Data granularity is 30 minutes.
    """
    now = datetime.utcnow()
    # Adjust time to the nearest 30-minute mark
    now = now.replace(minute=30 if now.minute >= 30 else 0, second=0, microsecond=0)
    
    raw_data_entries = []
    
    # Generate data for the past 24 hours (24 * 2 = 48 data points)
    for i in range(48):
        time_point = now - timedelta(minutes=30 * i)
        timestamp_str = time_point.isoformat() + "Z"
        
        # Simulate base commit counts (random fluctuation)
        # BTC/ETH are usually higher, others are lower
        base_activity = random.randint(0, 15) if symbol in ["BTC", "ETH"] else random.randint(0, 5)
        
        # Occasional bursts (Merge Request merges)
        if random.random() > 0.9:
            base_activity += random.randint(10, 30)
            
        # Simulate core developer ratio (usually a small fraction of total commits)
        core_dev_count = int(base_activity * random.uniform(0.2, 0.6))
        
        # Construct a single record similar to an API response
        entry = {
            "collected_at": timestamp_str,
            "repo_stats": {
                "total_commits": base_activity,
                "core_contributors_commits": core_dev_count,
                # Add some "noise" data to make it look like raw scraper data
                "active_repos": random.randint(1, 5),
                "unique_authors": max(1, int(base_activity / 2)) if base_activity > 0 else 0,
                "latest_commit_hash": str(uuid.uuid4())[:8] if base_activity > 0 else None
            }
        }
        raw_data_entries.append(entry)
    
    # Sort by time in ascending order (Old -> New)
    raw_data_entries.reverse()
    
    # Construct the final JSON structure
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
    # 1. Build path
    # Use os.path.abspath to ensure correct path resolution
    base_dir = os.path.abspath(os.path.join(".", "CODE_GEN", "developer"))
    
    if not os.path.exists(base_dir):
        print(f"Creating directory: {base_dir}")
        os.makedirs(base_dir)
        
    file_path = os.path.join(base_dir, f"{symbol}.txt")
    
    # 2. Write JSON
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
        
    print(f"✅ [Scraper Mock] Saved raw data for {symbol} to {file_path}")

if __name__ == "__main__":
    print("--- Starting Mock Scraper (Last 24h) ---")
    for sym in TARGET_SYMBOLS:
        raw_json = generate_scraped_data(sym)
        save_raw_file(sym, raw_json)