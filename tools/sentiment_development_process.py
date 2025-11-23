# social_dev_metrics_builder.py

import pandas as pd
import numpy as np

# --- sentiment development metrics ---

def calculate_sentiment_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates metrics based on social media sentiment scores.

    Input DataFrame (df) MUST contain: 
        'Sentiment_Score' column (NLP-derived score, e.g., -1 to 1). (30-min granularity assumed)

    Output: 
        DataFrame with added columns: 'Sentiment_MA_8', 'Sentiment_ZScore', 'Extreme_Sentiment'.

    Calculation Process:
    1. Sentiment_MA_8: Simple Moving Average of the Sentiment Score over 8 periods (4 hours) for smoothing.
    2. Sentiment_ZScore: Z-Score of the current Sentiment Score relative to the 48-period (24 hours) mean and standard deviation.
    3. Extreme_Sentiment: The Z-Score value if the absolute Z-Score is > 2.0, otherwise 0. Identifies emotional extremes.
    """
    df = df.copy()
    
    # 1. Sentiment Moving Average
    df['Sentiment_MA_8'] = df['Sentiment_Score'].rolling(window=8).mean()
    
    # 2. Sentiment Z-Score (Extremity)
    window_zscore = 48 
    df['Sentiment_Std'] = df['Sentiment_Score'].rolling(window=window_zscore).std()
    df['Sentiment_Mean'] = df['Sentiment_Score'].rolling(window=window_zscore).mean()
    df['Sentiment_ZScore'] = (df['Sentiment_Score'] - df['Sentiment_Mean']) / df['Sentiment_Std']
    
    # 3. Extreme Sentiment Signal
    df['Extreme_Sentiment'] = np.where(np.abs(df['Sentiment_ZScore']) > 2.0, df['Sentiment_ZScore'], 0)

    return df

# --- development metrics ---

def calculate_development_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates metrics based on project development activity.

    Input DataFrame (df) MUST contain: 
        'Commit_Count', 'Core_Dev_Commits' columns. (30-min granularity assumed)

    Output: 
        DataFrame with added columns: 'Core_Dev_MA_7D', 'Dev_Activity_Signal', 'Total_Commits_Acc_144'.

    Calculation Process:
    1. Core_Dev_MA_7D: 7-day (336 periods) Moving Average of commits from core developers.
    2. Dev_Activity_Signal: Ratio of current Core_Dev_Commits to Core_Dev_MA_7D (current activity vs. long-term average).
    3. Total_Commits_Acc_144: Cumulative sum of all commits over 144 periods (72 hours).
    """
    df = df.copy()

    # 1. Core Developer Commit Moving Average
    df['Core_Dev_MA_7D'] = df['Core_Dev_Commits'].rolling(window=336).mean()
    
    # 2. Core Developer Activity Signal (Current vs. Mean)
    df['Dev_Activity_Signal'] = df['Core_Dev_Commits'] / df['Core_Dev_MA_7D']
    
    # 3. Total Commits Accumulation (3 days)
    df['Total_Commits_Acc_144'] = df['Commit_Count'].rolling(window=144).sum()

    return df 