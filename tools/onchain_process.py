# onchain_metrics_builder.py

import pandas as pd
import numpy as np
import json
import os

# --- 1. Metric Calculation Functions (Provided by you) ---

def calculate_onchain_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates key on-chain ratio metrics: MVRV and SOPR.

    Input DataFrame (df) MUST contain: 
        'Close', 'UTXO_Realized_Price', 'SOPR_Raw' columns. (30-min granularity assumed)

    Output: 
        DataFrame with added columns: 'MVRV_Ratio', 'SOPR_MA_7', 'SOPR_Signal'.
    """
    df = df.copy()

    # 1. MVRV (Market Value to Realized Value) Ratio
    # Assumes 'UTXO_Realized_Price' represents the Realized Value per coin.
    if 'Close' in df.columns and 'UTXO_Realized_Price' in df.columns:
        df['MVRV_Ratio'] = df['Close'] / df['UTXO_Realized_Price']
    else:
        df['MVRV_Ratio'] = np.nan
    
    # 2. SOPR (Spent Output Profit Ratio) Moving Average
    if 'SOPR_Raw' in df.columns:
        df['SOPR_MA_7'] = df['SOPR_Raw'].rolling(window=7).mean()
        # 3. SOPR Signal (Profitability check)
        df['SOPR_Signal'] = np.where(df['SOPR_MA_7'] > 1.0, 1, 0)
    
    return df

def calculate_onchain_flows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates on-chain flow metrics: Exchange Netflow and Non-Zero Address Growth.

    Input DataFrame (df) MUST contain: 
        'Exchange_Netflow_USD', 'Non_Zero_Addresses' columns. (30-min granularity assumed)

    Output: 
        DataFrame with added columns: 'Netflow_Acc_48', 'Netflow_Signal', 'NZ_Address_Growth_48'.
    """
    df = df.copy()
    
    # 1. Exchange Netflow Accumulation
    if 'Exchange_Netflow_USD' in df.columns:
        df['Netflow_Acc_48'] = df['Exchange_Netflow_USD'].rolling(window=48).sum()
        # 2. Netflow Signal (Accumulation vs. Distribution)
        df['Netflow_Signal'] = np.where(df['Netflow_Acc_48'] < 0, 1, -1) 

    # 3. Non-Zero Addresses Growth Rate
    if 'Non_Zero_Addresses' in df.columns:
        df['NZ_Address_Growth_48'] = df['Non_Zero_Addresses'].pct_change(periods=48)
    
    return df

# --- 2. Data Loader & Parser ---

def load_raw_chain_data(symbol: str) -> pd.DataFrame:
    """
    Reads JSON from ../CODE_GEN/chain/{symbol}.txt and flattens it into a DataFrame.
    
    Crucial Step: 
    Since the simulator produces nested JSON (e.g., 'valuation_metrics.utxo_realized_price'),
    this function maps those nested fields to the columns expected by the calculation functions.
    """
    file_path = os.path.join("..", "CODE_GEN", "chain", f"{symbol}.txt")
    
    if not os.path.exists(file_path):
        print(f"Error: Chain data file not found for {symbol}")
        return pd.DataFrame()
        
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_json = json.load(f)
        
    entries = raw_json.get("chain_data", [])
    if not entries:
        return pd.DataFrame()
        
    # Flatten the nested JSON structure
    data_list = []
    for entry in entries:
        # Extract nested dictionaries
        val_metrics = entry.get("valuation_metrics", {})
        net_activity = entry.get("network_activity", {})
        supply_dist = entry.get("supply_distribution", {})
        
        # 1. Get Base Data
        utxo_price = val_metrics.get("utxo_realized_price", 0)
        active_addr = net_activity.get("active_addresses", 0)
        whale_bal = supply_dist.get("whale_aggregate_balance", 0)
        
        # 2. Derive/Simulate Missing Columns (Since simulator might not output Market Close directly)
        # In a real app, you would merge this with market_data (OHLCV).
        # Here, we simulate 'Close' relative to Realized Price to allow MVRV calc.
        simulated_close = utxo_price * 1.15 # Assuming market is slightly above realized price
        
        # Simulate SOPR (Fluctuating around 1.0)
        simulated_sopr = 1.0 + (np.random.random() - 0.5) * 0.05
        
        # Simulate Netflow based on Whale Balance changes (Proxy)
        # Note: We can't calc delta here easily row-by-row without DF, so we store raw balance first
        
        row = {
            "timestamp": entry.get("timestamp"),
            "UTXO_Realized_Price": utxo_price,
            "Non_Zero_Addresses": active_addr, # Using active addresses as proxy
            "Whale_Balance": whale_bal,
            "Close": simulated_close,          # Synthetic for demo
            "SOPR_Raw": simulated_sopr         # Synthetic for demo
        }
        data_list.append(row)
        
    df = pd.DataFrame(data_list)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # Calculate Netflow from Whale Balance Change (Negative change = Outflow/Sell, Positive = Inflow/Buy)
    # *Note*: For Exchange Netflow, Inflow is usually bad (sell pressure). 
    # Here we treat Whale Inflow as Accumulation (Good). 
    # To match function expectation (Exchange Netflow), we might inverse logic or just use raw diff.
    # Let's assume this column represents "Flow TO Exchanges".
    df['Exchange_Netflow_USD'] = -df['Whale_Balance'].diff() * df['Close']
    
    return df

# --- 3. Master Analysis Function ---

def chain_data_analysis(symbol: str) -> pd.DataFrame:
    """
    Wrapper function to load raw on-chain data and calculate all ratio and flow metrics.

    Input:
        symbol (str): Ticker symbol (e.g., "BTC"). 
                      Requires '../CODE_GEN/chain/{symbol}.txt'.

    Output:
        pd.DataFrame: DataFrame with columns:
                      [UTXO_Realized_Price, Non_Zero_Addresses, Close, SOPR_Raw, 
                       MVRV_Ratio, SOPR_MA_7, SOPR_Signal, 
                       Netflow_Acc_48, Netflow_Signal, NZ_Address_Growth_48]
    """
    # 1. Load and Parse
    df = load_raw_chain_data(symbol)
    
    if df.empty:
        print(f"No chain data found for {symbol}")
        return df
        
    # 2. Calculate Ratios (MVRV, SOPR)
    df = calculate_onchain_ratios(df)
    
    # 3. Calculate Flows (Netflow, Growth)
    df = calculate_onchain_flows(df)
    
    return df