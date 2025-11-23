# technical_metrics_builder.py

import pandas as pd
import numpy as np
import json
import os
import ta

# Import specific indicators
from ta.trend import EMAIndicator, SMAIndicator, MACD, CCIIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, ChaikinMoneyFlowIndicator

# --- 1. Data Loading ---

def load_data_by_symbol(symbol):
    """
    Reads a JSON file for a specific symbol and converts the 'bars' list into a Pandas DataFrame.
    path: CODE_GEN/resources/{symbol}.txt
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "resources", f"{symbol}.txt")

    if not os.path.exists(file_path):
        # Fallback for relative paths if run from root
        file_path = os.path.join("CODE_GEN", "resources", f"{symbol}.txt")
        if not os.path.exists(file_path):
             return pd.DataFrame()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return pd.DataFrame()

    bars = data.get('bars', [])
    if not bars:
        return pd.DataFrame()

    df = pd.DataFrame(bars)

    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)

    core_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in core_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    return df

# --- 2. Basic Indicators Calculation ---

def calculate_indicators(df):
    """Calculates standard technical indicators."""
    df = df.copy()
    if len(df) < 14: return df 

    # Trend
    # (Intermediate MAs removed from final output, but needed for calculation if referencing later)
    # We keep MACD Hist as it shows momentum shift
    macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
    df['MACD_Hist'] = macd.macd_diff() # Predictive of crossovers
    
    df['CCI_14'] = CCIIndicator(high=df['high'], low=df['low'], close=df['close'], window=14).cci()

    # Momentum
    df['RSI_14'] = RSIIndicator(close=df['close'], window=14).rsi()
    
    # Volatility
    df['ATR_14'] = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14).average_true_range()
    
    bb = BollingerBands(close=df['close'], window=20, window_dev=2.0)
    # Calculate %B (Percent Bandwidth) - shows where price is relative to bands (0=Lower, 1=Upper)
    # This is more predictive/actionable than just raw band values
    df['BB_Pct_B'] = (df['close'] - bb.bollinger_lband()) / (bb.bollinger_hband() - bb.bollinger_lband())
    
    # Volume
    df['OBV_calc'] = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume()

    return df

# --- 3. Advanced Metrics Calculation ---

def calculate_advanced_metrics(df):
    """Calculates advanced market structure metrics."""
    df = df.copy()
    if len(df) < 24: return df

    # A. VWAP Deviation (Predictive of Mean Reversion)
    v = df['volume'].values
    tp = (df['high'] + df['low'] + df['close']) / 3
    vwap = (pd.Series(tp * v).rolling(window=24).sum() / pd.Series(v).rolling(window=24).sum())
    # Metric: Percentage distance from VWAP
    df['VWAP_Dev_Pct'] = ((df['close'] - vwap) / vwap) * 100

    # B. CMF (Trend Confirmation)
    df['CMF_20'] = ChaikinMoneyFlowIndicator(
        high=df['high'], low=df['low'], close=df['close'], volume=df['volume'], window=20
    ).chaikin_money_flow()

    # C. CHOP (Market State)
    high_low_diff = df['high'] - df['low']
    atr_sum = high_low_diff.rolling(window=14).sum()
    high_max = df['high'].rolling(window=14).max()
    low_min = df['low'].rolling(window=14).min()
    range_diff = high_max - low_min
    df['CHOP_14'] = 100 * np.log10(atr_sum / range_diff.replace(0, np.nan)) / np.log10(14)

    # D. Linear Regression Outlier Signal
    window = 20
    x_range = np.arange(window)
    def rolling_linreg(y_window):
        m, c = np.polyfit(x_range, y_window, 1)
        return m * (window - 1) + c

    lin_mid = df['close'].rolling(window=window).apply(rolling_linreg, raw=True)
    lin_std = df['close'].rolling(window=window).std()
    lin_upper = lin_mid + (2 * lin_std)
    lin_lower = lin_mid - (2 * lin_std)
    
    # Signal: 1 (Overbought), -1 (Oversold), 0 (Normal)
    df['Reg_Outlier_Signal'] = np.where(
        df['close'] > lin_upper, 1, 
        np.where(df['close'] < lin_lower, -1, 0)
    )

    return df

# --- 4. Master Function (Filtered Output) ---

def market_data_analysis(symbol):
    """
    Loads data and returns a concise DataFrame of HIGH-VALUE, PREDICTIVE indicators.
    Removes raw price columns (Open/High/Low) and intermediate Moving Averages.
    """
    # 1. Load
    df = load_data_by_symbol(symbol)
    if df.empty:
        return df
        
    # Preserve Close price for context, but drop others later
    df['Close_Price'] = df['close'] 

    # 2. Calculate All
    df = calculate_indicators(df)
    df = calculate_advanced_metrics(df)
    
    # 3. Filter for Predictive/High-Order Metrics Only
    # We define the list of actionable signals
    predictive_columns = [
        'Close_Price',          # Context
        'RSI_14',               # Momentum (Oversold/Overbought)
        'MACD_Hist',            # Momentum Change (Divergence/Crossover proxy)
        'CCI_14',               # Cyclic Trend
        'BB_Pct_B',             # Volatility Position (0 to 1)
        'ATR_14',               # Volatility Magnitude (for Stop Loss sizing)
        'CMF_20',               # Money Flow Pressure
        'VWAP_Dev_Pct',         # Mean Reversion Potential
        'CHOP_14',              # Market Regime (Trend vs Range)
        'Reg_Outlier_Signal',   # Statistical Extremes
        'OBV_calc'              # Volume Trend
    ]
    
    # Select only existing columns (intersection) to avoid errors on short data
    final_cols = [c for c in predictive_columns if c in df.columns]
    
    return df[final_cols]