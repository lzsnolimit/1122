import json
import os
import random
import uuid
from datetime import datetime, timedelta

# Define the symbols to simulate
TARGET_SYMBOLS = ["USDT", "BTC", "ETH", "USDC", "SOL", "XRP", "ZEC", "BNB", "DOGE"]

def generate_chain_data(symbol):
    """
    Simulates raw on-chain data for the past 24 hours with 30-minute granularity.
    
    Data points included:
    1. Block Info: Block Height, Block Time.
    2. UTXO/Asset Info: Realized Price (proxy for UTXO value), UTXO Count (implied).
    3. Transactions: Tx Count, Tx Volume (Amount), Avg Gas Fee.
    4. Network Activity: Active Addresses, New Addresses.
    5. Whale Activity: Whale Wallet Balance (Top 100 aggregate).
    """
    now = datetime.utcnow()
    # Adjust to the nearest 30-minute mark
    now = now.replace(minute=30 if now.minute >= 30 else 0, second=0, microsecond=0)
    
    chain_data_entries = []
    
    # Base parameters for simulation (different scales for BTC/ETH vs others)
    is_major = symbol in ["BTC", "ETH"]
    
    # Initial states for cumulative metrics
    current_block_height = 8000000 + random.randint(0, 100000)
    current_whale_balance = 5000000 if is_major else 100000000 # Abstract units
    
    # Generate data for the past 24 hours (48 periods of 30 mins)
    for i in range(48):
        time_point = now - timedelta(minutes=30 * i)
        timestamp_str = time_point.isoformat() + "Z"
        
        # --- 1. Block Info ---
        # Blocks produced in 30 mins (approx 10 mins per block for BTC, 12s for ETH)
        blocks_added = 3 if symbol == "BTC" else (150 if symbol == "ETH" else 400)
        current_block_height -= blocks_added # Working backwards in time loop
        
        # --- 2. Transactions & Fees ---
        # Random fluctuation based on network busyness
        busyness = random.uniform(0.8, 1.5)
        
        tx_count = int((2000 if is_major else 500) * busyness)
        tx_volume = (50000000 if is_major else 10000000) * busyness * random.uniform(0.5, 2.0)
        
        # Gas Fee (Higher when busy)
        base_fee = 5.0 if symbol == "ETH" else (2.0 if symbol == "BTC" else 0.01)
        avg_gas_fee = base_fee * (busyness ** 2)
        
        # --- 3. Network Addresses ---
        active_addresses = int(tx_count * random.uniform(1.2, 1.8))
        new_addresses = int(active_addresses * random.uniform(0.05, 0.15))
        
        # --- 4. UTXO / Valuation (Simulated) ---
        # Realized Price often trails market price. Simulating a slow moving average.
        # We assume a base price for simplicity.
        base_price = 60000 if symbol == "BTC" else (3000 if symbol == "ETH" else 100)
        utxo_realized_price = base_price * random.uniform(0.8, 0.95) # Usually lower than current price in bull market
        
        # --- 5. Whale Activity ---
        # Random inflow/outflow from whales
        whale_flow = random.uniform(-5000, 5000) * (10 if not is_major else 1)
        current_whale_balance -= whale_flow # Reversing the flow since we loop backwards
        
        entry = {
            "timestamp": timestamp_str,
            "block_summary": {
                "height": current_block_height,
                "block_time_avg": 600 if symbol == "BTC" else 12 # seconds
            },
            "transaction_metrics": {
                "count": tx_count,
                "volume_usd": round(tx_volume, 2),
                "avg_fee_usd": round(avg_gas_fee, 4)
            },
            "network_activity": {
                "active_addresses": active_addresses,
                "new_addresses": new_addresses
            },
            "valuation_metrics": {
                "utxo_realized_price": round(utxo_realized_price, 2)
            },
            "supply_distribution": {
                "whale_aggregate_balance": round(current_whale_balance, 2)
            }
        }
        chain_data_entries.append(entry)
        
    # Sort by time in ascending order (Old -> New)
    chain_data_entries.reverse()
    
    # Construct final JSON
    final_json = {
        "symbol": symbol,
        "source": "chain_node_simulator_v1",
        "meta": {
            "generated_at": datetime.utcnow().isoformat(),
            "period": "24h",
            "granularity": "30min"
        },
        "chain_data": chain_data_entries
    }
    
    return final_json

def save_chain_file(symbol, data):
    # Construct path: ../CODE_GEN/chain/{symbol}.txt
    base_dir = os.path.abspath(os.path.join(".", "CODE_GEN", "chain"))
    
    if not os.path.exists(base_dir):
        print(f"Creating directory: {base_dir}")
        os.makedirs(base_dir)
        
    file_path = os.path.join(base_dir, f"{symbol}.txt")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
        
    print(f"✅ [Chain Sim] Saved on-chain data for {symbol} to {file_path}")

if __name__ == "__main__":
    print("--- Starting Chain Data Simulation (Last 24h) ---")
    for sym in TARGET_SYMBOLS:
        chain_json = generate_chain_data(sym)
        save_chain_file(sym, chain_json)