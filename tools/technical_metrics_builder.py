# technical_metrics_builder.py

import pandas as pd
import numpy as np
try:
    import talib
except ImportError:
    talib = None

# --- technical indicator ---

def calculate_ta_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates standard Technical Analysis (TA) indicators: MA, RSI, MACD, BBands.

    Input DataFrame (df) MUST contain: 
        'Close', 'High', 'Low' columns. (30-min granularity assumed)

    Output: 
        DataFrame with added columns: 'MA_20', 'RSI_14', 'MACD', 'MACD_Signal', 'BB_Upper', 'BB_Lower'.

    Calculation Process:
    1. MA_20: Simple Moving Average over 20 periods (10 hours).
    2. RSI_14: Relative Strength Index over 14 periods (7 hours).
    3. MACD: Calculated using standard 12, 26, 9 periods (EMA based).
    4. BBands: Bollinger Bands over 20 periods with 2 standard deviations.
    """
    df = df.copy()

    # 1. Moving Average (MA)
    df['MA_20'] = df['Close'].rolling(window=20).mean()
    
    if talib:
        # 2. RSI (Relative Strength Index)
        df['RSI_14'] = talib.RSI(df['Close'].values, timeperiod=14)
        
        # 3. MACD (Moving Average Convergence Divergence)
        macd, macdsignal, _ = talib.MACD(df['Close'].values, fastperiod=12, slowperiod=26, signalperiod=9)
        df['MACD'] = macd
        df['MACD_Signal'] = macdsignal
        
        # 4. Bollinger Bands (BBands)
        upper, _, lower = talib.BBANDS(df['Close'].values, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        df['BB_Upper'] = upper
        df['BB_Lower'] = lower
    else:
        # Simple Pandas RSI fallback (if TA-Lib is unavailable)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        RS = gain / loss
        df['RSI_14_Panda'] = 100 - (100 / (1 + RS))
        
    return df

# --- derivatives metrics ---

def calculate_derivatives_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates metrics based on derivatives data (Funding Rate and Open Interest).

    Input DataFrame (df) MUST contain: 
        'Funding_Rate', 'Open_Interest' columns. (30-min granularity assumed)

    Output: 
        DataFrame with added columns: 'FR_MA_48', 'FR_Std_48', 'FR_Slope_8', 'OI_Change_Rate'.

    Calculation Process:
    1. FR_MA_48: 48-period (24 hours) Moving Average of Funding Rate.
    2. FR_Std_48: 48-period Standard Deviation of Funding Rate (measures volatility).
    3. FR_Slope_8: Linear regression slope of Funding Rate over 8 periods (4 hours), indicating trend direction.
    4. OI_Change_Rate: Percentage change in Open Interest over 4 periods (2 hours), indicating leverage inflow/outflow speed.
    """
    df = df.copy()
    
    # 1. Funding Rate Moving Average
    df['FR_MA_48'] = df['Funding_Rate'].rolling(window=48).mean()
    
    # 2. Funding Rate Standard Deviation
    df['FR_Std_48'] = df['Funding_Rate'].rolling(window=48).std()
    
    # 3. Funding Rate Slope (Trend)
    df['FR_Slope_8'] = df['Funding_Rate'].rolling(window=8).apply(
        lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=True
    )
    
    # 4. Open Interest Change Rate
    df['OI_Change_Rate'] = df['Open_Interest'].pct_change(periods=4)

    return df

# Example Data Structure (Input DataFrame should at least include these columns)
# required_cols = ['Close', 'High', 'Low', 'Volume', 'Funding_Rate', 'Open_Interest']