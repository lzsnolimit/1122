# technical_metrics_builder.py

import pandas as pd
import numpy as np  # Added numpy for advanced math (Log10, Polyfit)
import json
import os
import ta  

# Import specific indicators
from ta.trend import EMAIndicator, SMAIndicator, MACD, CCIIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, ChaikinMoneyFlowIndicator # Added CMF

# --- 1. Data Loading ---

def load_data_by_symbol(symbol):
    """
    Reads a JSON file for a specific symbol and converts the 'bars' list into a Pandas DataFrame.
    
    Path Logic:
    Resolves the file path relative to this module directory to be robust
    against different current working directories, at:
    CODE_GEN/resources/{symbol}.txt
    """
    # Construct the file path relative to this file's directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "resources", f"{symbol}.txt")

    # Check if file exists
    if not os.path.exists(file_path):
        # Print absolute path to help debugging
        abs_path = os.path.abspath(file_path)
        raise FileNotFoundError(f"File not found for symbol '{symbol}' at: {abs_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON for {symbol}.")
        return pd.DataFrame()

    # Extract 'bars' data
    bars = data.get('bars', [])
    if not bars:
        print(f"Warning: No 'bars' data found in JSON for {symbol}.")
        return pd.DataFrame()

    # Convert to DataFrame
    df = pd.DataFrame(bars)

    # 1. Handle Timestamp
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)

    # 2. Ensure core OHLCV columns are numeric
    core_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in core_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 3. Auto-process remaining columns (existing indicators from JSON)
    indicator_cols = [c for c in df.columns if c not in core_cols]
    for col in indicator_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    print(f"Successfully loaded data for {symbol}: {len(df)} rows")
    return df

# --- 2. Basic Indicators Calculation ---

def calculate_indicators(df):
    """
    Calculates standard technical indicators based on OHLCV data using the 'ta' library.
    """
    df = df.copy()
    
    if len(df) < 14:
        print("Warning: Not enough data rows to calculate long-period indicators.")
        return df 

    # --- Trend ---
    df['EMA_12'] = EMAIndicator(close=df['close'], window=12).ema_indicator()
    df['EMA_26'] = EMAIndicator(close=df['close'], window=26).ema_indicator()
    df['SMA_20'] = SMAIndicator(close=df['close'], window=20).sma_indicator()
    
    macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
    df['MACD_12_26_9'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Hist'] = macd.macd_diff()
    
    df['CCI_14'] = CCIIndicator(high=df['high'], low=df['low'], close=df['close'], window=14).cci()

    # --- Momentum ---
    df['RSI_14'] = RSIIndicator(close=df['close'], window=14).rsi()
    
    stoch = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=5, smooth_window=3)
    df['STOCH_k'] = stoch.stoch()
    df['STOCH_d'] = stoch.stoch_signal()
    
    # --- Volatility ---
    df['ATR_14'] = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14).average_true_range()
    
    bb_indicator = BollingerBands(close=df['close'], window=20, window_dev=2.0)
    df['BB_Upper'] = bb_indicator.bollinger_hband()
    df['BB_Lower'] = bb_indicator.bollinger_lband()
    df['BB_Middle'] = bb_indicator.bollinger_mavg()
    
    # --- Volume ---
    df['OBV_calc'] = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume()

    return df

# --- 3. Advanced Metrics Calculation (New Added Section) ---

def calculate_advanced_metrics(df):
    """
    Calculates advanced market structure metrics:
    1. VWAP (Rolling 24-period)
    2. CMF (Chaikin Money Flow)
    3. CHOP (Choppiness Index)
    4. Linear Regression Channel (Confidence Intervals)
    """
    df = df.copy()
    
    if len(df) < 24:
        return df

    # --- A. VWAP (Volume Weighted Average Price) ---
    # Using a 24-period rolling window (e.g., 24 hours for 1h data)
    v = df['volume'].values
    tp = (df['high'] + df['low'] + df['close']) / 3
    df['VWAP_24'] = (pd.Series(tp * v).rolling(window=24).sum() / 
                     pd.Series(v).rolling(window=24).sum())

    # --- B. CMF (Chaikin Money Flow) ---
    df['CMF_20'] = ChaikinMoneyFlowIndicator(
        high=df['high'], low=df['low'], close=df['close'], volume=df['volume'], window=20
    ).chaikin_money_flow()

    # --- C. Choppiness Index (CHOP) ---
    # Formula: 100 * Log10(Sum(ATR, n) / (MaxHi(n) - MinLo(n))) / Log10(n)
    high_low_diff = df['high'] - df['low']
    atr_sum = high_low_diff.rolling(window=14).sum()
    high_max = df['high'].rolling(window=14).max()
    low_min = df['low'].rolling(window=14).min()
    range_diff = high_max - low_min
    
    # Avoid division by zero with replace
    df['CHOP_14'] = 100 * np.log10(atr_sum / range_diff.replace(0, np.nan)) / np.log10(14)

    # --- D. Linear Regression Channel (Confidence Intervals) ---
    # Simple implementation using rolling slope and intercept
    window = 20
    x_range = np.arange(window)
    
    def rolling_linreg(y_window):
        # y = mx + c
        m, c = np.polyfit(x_range, y_window, 1)
        # Return predicted value at the end of the window
        return m * (window - 1) + c

    # 1. Calculate the Linear Regression Line (Middle)
    df['LinReg_Mid'] = df['close'].rolling(window=window).apply(rolling_linreg, raw=True)
    
    # 2. Calculate Standard Deviation from that line
    df['LinReg_Std'] = df['close'].rolling(window=window).std()
    
    # 3. Upper and Lower Bands (2 Sigma Confidence Interval)
    df['LinReg_Upper'] = df['LinReg_Mid'] + (2 * df['LinReg_Std'])
    df['LinReg_Lower'] = df['LinReg_Mid'] - (2 * df['LinReg_Std'])
    
    # 4. Signal: Outlier Detection
    df['Price_Outlier'] = np.where(
        df['close'] > df['LinReg_Upper'], 1, # Overbought / Abnormal High
        np.where(df['close'] < df['LinReg_Lower'], -1, 0) # Oversold / Abnormal Low
    )

    return df

# --- 4. Master Function ---

def market_data_analysis(symbol):
    """
    Wrapper function to load data and apply ALL metrics (Basic + Advanced).
    """
    # 1. Load
    df = load_data_by_symbol(symbol)
    if df.empty:
        return df
        
    # 2. Basic Indicators
    df = calculate_indicators(df)
    
    # 3. Advanced Metrics 
    df = calculate_advanced_metrics(df)
    
    return df
