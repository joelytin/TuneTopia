# Steps:
# 1. Data preprocessing
# 2. Collaborative filtering
# 3. Content-based filtering
# 4. Hybrid filtering - combine collaborative and content-based filtering results

import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from scipy.sparse import csr_matrix

# Load the dataset
dataset = pd.read_csv('data/huggingface.csv')

# Data preprocessing
def preprocess_data(dataset):
    # Normalise numerical features
    scaler = StandardScaler()
    numerical_features = ['popularity', 'duration_ms', 'danceability', 'energy', 'key', 'loudness', 'mode', 'speechiness', 'acousticness', 'instrumentalness', 'liveness', 'valence', 'tempo', 'time_signature']
    dataset[numerical_features] = scaler.fit_transform(dataset[numerical_features])

    # Convert categorical features to one-hot encoding
    categorical_features = ['explicit', 'track_genre']
    dataset = pd.get_dummies(dataset, columns=categorical_features)

    return dataset

# Content-based filtering
def content_based_recommendations(track_id, dataset, top_n=10):
    # Find the index of the track_id in the dataset
    track_index = dataset.index[dataset['track_id'] == track_id].tolist()
    
    # Drop non-feature columns
    feature_columns = dataset.columns.difference(['track_id', 'artists', 'album_name', 'track_name'])
    track_features = dataset[feature_columns].values
    
    # Compute cosine similarities
    similarities = cosine_similarity([track_features[track_index]], track_features)[0]
    
    # Get top N similar tracks
    similar_indices = similarities.argsort()[-top_n-1:-1][::-1]
    
    return dataset.iloc[similar_indices]



# Collaborative filtering (using implicit feedback)
def collaborative_recommendations(user_tracks, dataset, top_n=10):
    # Ensure the dataset contains track data
    if 'track_id' not in dataset.columns:
        raise ValueError("Dataset must contain 'track_id' column.")
    
    # Create a dummy user-item matrix using track popularity as implicit feedback
    track_popularity = dataset.set_index('track_id')['popularity']
    item_similarities = cosine_similarity(track_popularity.values.reshape(-1, 1))
    item_similarities_df = pd.DataFrame(item_similarities, index=track_popularity.index, columns=track_popularity.index)

    # Aggregate scores for user tracks
    user_scores = np.zeros(len(track_popularity))
    for track_id in user_tracks:
        if track_id in item_similarities_df.columns:
            user_scores += item_similarities_df[track_id].values

    # Get top N recommendations
    recommended_indices = user_scores.argsort()[-top_n:][::-1]
    recommended_track_ids = item_similarities_df.columns[recommended_indices]
    
    return dataset[dataset['track_id'].isin(recommended_track_ids)]



# Hybrid filtering
def hybrid_recommendations(user_top_tracks, dataset, top_n=10):
    # Ensure `user_top_tracks` contains valid track IDs
    if not user_top_tracks:
        raise ValueError("User top tracks list is empty.")
    
    # Get content-based recommendations for each user top track
    content_recommendations = pd.DataFrame()
    for track in user_top_tracks:
        # Ensure track_id exists in dataset before passing
        if track not in dataset['track_id'].values:
            print(f"Warning: Track ID {track} not found in dataset.")
            continue
        
        recommendations = content_based_recommendations(track, dataset)
        content_recommendations = content_recommendations.append(recommendations)

    # Get collaborative recommendations
    collaborative_recommendations_df = collaborative_recommendations(user_top_tracks, dataset)

    # Combine and deduplicate recommendations
    combined_recommendations = pd.concat([content_recommendations, collaborative_recommendations_df]).drop_duplicates().head(top_n)
    return combined_recommendations