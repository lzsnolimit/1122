# sentiment_preprocessing_finbert.py

import pandas as pd
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# --- Stage I: Sentiment Analysis using FinBERT ---

# Load pre-trained FinBERT model and tokenizer
# We use the standard FinBERT model for general financial sentiment
MODEL_NAME = "ProsusAI/finbert" 
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)

# Map output index to sentiment labels
# FinBERT typically outputs probabilities for three classes: 0=Negative, 1=Neutral, 2=Positive
LABEL_MAP = {0: 'negative', 1: 'neutral', 2: 'positive'}


def get_raw_sentiment_score_finbert(text: str) -> float:
    """
    Generates a Raw Sentiment Score from text using the FinBERT model (Stage I).

    Input:
        text: The raw text content of a social media post (e.g., a tweet).

    Output:
        float: A calculated normalized score between -1.0 and 1.0 (e.g., -1*P_neg + 1*P_pos).

    Calculation Process:
    1. Tokenization: Tokenize the text for the BERT model.
    2. Prediction: Model outputs logits (scores) for Negative, Neutral, and Positive classes.
    3. Softmax: Convert logits to probabilities (P_neg, P_neu, P_pos).
    4. Normalization: Calculate a single continuous sentiment score by mapping probabilities:
       Score = P_positive - P_negative
       (The Neutral probability is implicitly handled by the difference).
    """
    if not isinstance(text, str) or len(text.strip()) == 0:
        return 0.0

    # 1. Tokenization and Input Preparation
    inputs = tokenizer(text, padding=True, truncation=True, return_tensors='pt', max_length=512)

    # 2. Prediction
    with torch.no_grad():
        outputs = model(**inputs)
        
    # 3. Softmax to get probabilities
    probabilities = torch.softmax(outputs.logits, dim=1).squeeze()
    
    # Check if probabilities tensor has the expected 3 dimensions (Negative, Neutral, Positive)
    if probabilities.numel() != 3:
        # Handle cases where the batch size might be odd (though unlikely with squeeze)
        return 0.0

    p_neg = probabilities[0].item()
    p_pos = probabilities[2].item()
    
    # 4. Normalization to continuous score [-1, 1]
    # Score = P(Positive) - P(Negative)
    raw_score = p_pos - p_neg
    
    return raw_score


# --- Stage II: Weighting and Aggregation (unchanged, but uses new raw score) ---
# ... (The rest of the `aggregate_sentiment_data` function from the previous response remains the same)
# ... (它会使用 get_raw_sentiment_score_finbert() 替代字典方法)
# ...

def aggregate_sentiment_data(raw_df: pd.DataFrame, freq: str = '30min') -> pd.DataFrame:
    """
    Performs weighting and aggregation to produce the final 
    time-series 'Sentiment_Score' (Stage II).

    Input DataFrame (raw_df) MUST contain (per post/comment):
        'Content': Raw text.
        'Timestamp': Time of post (datetime).
        'Likes': Number of likes/upvotes.
        'Comments': Number of comments/replies.
    """
    df = raw_df.copy()
    
    # 1. Generate Raw Sentiment Score using FinBERT
    # Note: Applying FinBERT to a large DataFrame can be slow. Batch processing is recommended for production.
    df['Raw_Score'] = df['Content'].apply(get_raw_sentiment_score_finbert)
    
    # 2. Calculate Interaction Weight
    df['Total_Interactions'] = df['Likes'] + df['Comments']
    df['Weight'] = np.log1p(df['Total_Interactions'])
    df['Weight'] = df['Weight'].replace(0, 1)

    # Calculate Weighted Score for aggregation
    df['Weighted_Score'] = df['Raw_Score'] * df['Weight']

    # Set Timestamp as index for resampling/grouping
    df = df.set_index('Timestamp').sort_index()

    # 3. Group and Aggregate (Weighted Average)
    weighted_sum = df['Weighted_Score'].resample(freq).sum()
    weight_sum = df['Weight'].resample(freq).sum()
    
    df_aggregated = pd.DataFrame({
        'Sentiment_Score': (weighted_sum / weight_sum)
    })
    
    df_aggregated['Sentiment_Score'] = df_aggregated['Sentiment_Score'].replace([np.inf, -np.inf], 0).fillna(0)

    return df_aggregated


if __name__ == "__main__":
    print("--- FinBERT-based Sentiment Preprocessing Demonstration ---")
    
    # 模拟原始社交数据 (Simulation of Raw Social Data)
    data = {
        'Content': [
            "The company reported a strong quarterly earnings beat, showing potential growth in market share.", 
            "I fear a massive sell-off is imminent due to global regulatory uncertainty.", 
            "Bitcoin is consolidating sideways, not much movement today.", 
            "The unexpected liquidation event caused panic selling."
        ],
        'Timestamp': pd.to_datetime([
            '2025-11-22 10:05:00', '2025-11-22 10:15:00', 
            '2025-11-22 10:35:00', '2025-11-22 10:45:00'
        ]),
        'Likes': [1000, 50, 5, 200],
        'Comments': [200, 20, 1, 50]
    }
    raw_social_data = pd.DataFrame(data)
    
    print("\nRaw Data:")
    print(raw_social_data)
    
    # 运行 FinBERT 聚合函数 (Run FinBERT aggregation function for 30-min frequency)
    aggregated_sentiment_df = aggregate_sentiment_data(raw_social_data, freq='30min')
    
    print("\nStage I & II Aggregated Result (30-min Sentiment Score):")
    print(aggregated_sentiment_df)
    
    # Note: Running this code will download FinBERT and may take a moment.