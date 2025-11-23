# technical_metrics_builder.py
import pandas as pd
import json
import os
import ta  # Using the 'ta' library

# Import specific indicators
from ta.trend import EMAIndicator, SMAIndicator, MACD, CCIIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator

def load_data_by_symbol(symbol):
    """
    Reads a JSON file for a specific symbol and converts the 'bars' list into a Pandas DataFrame.
    
    Path Logic:
    It looks for the file at: ../CODE_GEN/resources/{symbol}.txt
    
    Args:
        symbol (str): The asset symbol (e.g., "BTC", "ETH").
        
    Returns:
        pd.DataFrame: DataFrame containing OHLCV and any original indicators.
    """
    # Construct the relative file path
    # using os.path.join ensures cross-platform compatibility (Windows/Linux)
    file_path = os.path.join("..", "CODE_GEN", "resources", f"{symbol}.txt")

    # Check if file exists
    if not os.path.exists(file_path):
        # Print absolute path to help debugging if file is not found
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

    # 3. Auto-process remaining columns (existing indicators from JSON like obv_, rsi_14)
    indicator_cols = [c for c in df.columns if c not in core_cols]
    for col in indicator_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    print(f"Successfully loaded data for {symbol}: {len(df)} rows")
    return df

def calculate_indicators(df):
    """
    Calculates standard technical indicators based on OHLCV data using the 'ta' library.
    """
    # Create a copy to avoid modifying the original DataFrame reference
    df = df.copy()
    
    # Ensure there is enough data for calculation
    if len(df) < 14:
        print("Warning: Not enough data rows to calculate long-period indicators.")
        return df # Return early to avoid errors

    # --- Trend Indicators ---
    
    # EMA (Exponential Moving Average)
    df['EMA_12'] = EMAIndicator(close=df['close'], window=12).ema_indicator()
    df['EMA_26'] = EMAIndicator(close=df['close'], window=26).ema_indicator()
    
    # SMA (Simple Moving Average)
    df['SMA_20'] = SMAIndicator(close=df['close'], window=20).sma_indicator()
    
    # MACD (Moving Average Convergence Divergence)
    macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
    df['MACD_12_26_9'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Hist'] = macd.macd_diff()
    
    # CCI (Commodity Channel Index)
    df['CCI_14'] = CCIIndicator(high=df['high'], low=df['low'], close=df['close'], window=14).cci()

    # --- Momentum Indicators ---
    
    # RSI (Relative Strength Index)
    df['RSI_14'] = RSIIndicator(close=df['close'], window=14).rsi()
    
    # Stochastic Oscillator (Stoch)
    stoch = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=5, smooth_window=3)
    df['STOCH_k'] = stoch.stoch()
    df['STOCH_d'] = stoch.stoch_signal()
    
    # --- Volatility Indicators ---
    
    # ATR (Average True Range)
    df['ATR_14'] = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14).average_true_range()
    
    # Bollinger Bands
    bb_indicator = BollingerBands(close=df['close'], window=20, window_dev=2.0)
    df['BB_Upper'] = bb_indicator.bollinger_hband()
    df['BB_Lower'] = bb_indicator.bollinger_lband()
    df['BB_Middle'] = bb_indicator.bollinger_mavg()
    
    # --- Volume Indicators ---
    
    # OBV (On-Balance Volume)
    df['OBV_calc'] = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume()

    return df