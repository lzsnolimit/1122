# onchain_metrics_builder.py

import pandas as pd
import numpy as np

# --- onchain ratios ---

def calculate_onchain_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates key on-chain ratio metrics: MVRV and SOPR.

    Input DataFrame (df) MUST contain: 
        'Close', 'UTXO_Realized_Price', 'SOPR_Raw' columns. (30-min granularity assumed)

    Output: 
        DataFrame with added columns: 'MVRV_Ratio', 'SOPR_MA_7', 'SOPR_Signal'.

    Calculation Process:
    1. MVRV_Ratio: Close Price / UTXO Realized Price (simplified version).
    2. SOPR_MA_7: Simple Moving Average of the aggregated SOPR_Raw value over 7 periods (3.5 hours) for smoothing.
    3. SOPR_Signal: Binary signal (1 or 0) indicating if SOPR_MA_7 is greater than 1.0 (profitable selling dominance).
    """
    df = df.copy()

    # 1. MVRV (Market Value to Realized Value) Ratio
    # Assumes 'UTXO_Realized_Price' represents the Realized Value per coin.
    df['MVRV_Ratio'] = df['Close'] / df['UTXO_Realized_Price']
    
    # 2. SOPR (Spent Output Profit Ratio) Moving Average
    df['SOPR_MA_7'] = df['SOPR_Raw'].rolling(window=7).mean()
    
    # 3. SOPR Signal (Profitability check)
    df['SOPR_Signal'] = np.where(df['SOPR_MA_7'] > 1.0, 1, 0)

    return df

# --- onchain flows ---

def calculate_onchain_flows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates on-chain flow metrics: Exchange Netflow and Non-Zero Address Growth.

    Input DataFrame (df) MUST contain: 
        'Exchange_Netflow_USD', 'Non_Zero_Addresses' columns. (30-min granularity assumed)

    Output: 
        DataFrame with added columns: 'Netflow_Acc_48', 'Netflow_Signal', 'NZ_Address_Growth_48'.

    Calculation Process:
    1. Netflow_Acc_48: Sum of Exchange Netflow over 48 periods (24 hours), measuring accumulation/distribution.
    2. Netflow_Signal: Binary signal (1 for accumulation/outflow, -1 for distribution/inflow).
    3. NZ_Address_Growth_48: Percentage change in Non-Zero Addresses over 48 periods (24 hours), measuring network adoption rate.
    """
    df = df.copy()
    
    # 1. Exchange Netflow Accumulation
    df['Netflow_Acc_48'] = df['Exchange_Netflow_USD'].rolling(window=48).sum()
    
    # 2. Netflow Signal (Accumulation vs. Distribution)
    df['Netflow_Signal'] = np.where(df['Netflow_Acc_48'] < 0, 1, -1) 

    # 3. Non-Zero Addresses Growth Rate
    df['NZ_Address_Growth_48'] = df['Non_Zero_Addresses'].pct_change(periods=48)
    
    return df