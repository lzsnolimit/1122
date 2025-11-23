# development_process.py

import pandas as pd
import numpy as np

# --- development_metrics ---

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