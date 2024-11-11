import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity

# Load the dataset
df = pd.read_csv('https://raw.githubusercontent.com/joelytin/TuneTopia/refs/heads/main/data/huggingface.csv?token=GHSAT0AAAAAACZSWHEIRJNSMMMDX5JF55TYZZOEQDA')

# Select relevant features
features = ['danceability', 'energy', 'loudness', 'speechiness', 'acousticness',
            'instrumentalness', 'liveness', 'valence', 'tempo']
X = df[features]

# Normalize the data
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Create a DataFrame for the normalized features
X_normalized = pd.DataFrame(X_scaled, columns=features)

# Function to recommend tracks based on pairwise similarity calculation
def recommend_similar_tracks(input_track_names, df, X_normalized, top_n=10):
    recommendations = []

    for track_name in input_track_names:
        # Find the index of the input track in the dataset
        try:
            track_index = df.index[df['track_name'] == track_name].tolist()[0]
        except IndexError:
            print(f"Track '{track_name}' not found in the dataset.")
            continue

        # Get the feature vector of the input track
        input_vector = X_normalized.iloc[track_index].values.reshape(1, -1)

        # Calculate cosine similarity between the input track and all other tracks
        similarity_scores = cosine_similarity(input_vector, X_normalized).flatten()

        # Sort by similarity score in descending order and exclude the track itself
        sorted_indices = np.argsort(-similarity_scores)
        sorted_indices = [i for i in sorted_indices if i != track_index]

        # Retrieve top N similar tracks
        top_similar_indices = sorted_indices[:top_n]
        similar_tracks = df.iloc[top_similar_indices]

        # Add recommendations for each input track
        recommendations.append(similar_tracks[['track_id', 'track_name', 'artists']])

    # Combine recommendations from all input tracks and drop duplicates
    final_recommendations = pd.concat(recommendations).drop_duplicates().head(top_n)
    return final_recommendations

# Example usage with 3 input tracks
input_track_names = ['Comedy', 'Ghost - Acoustic', 'To Begin Again']
recommendations = recommend_similar_tracks(input_track_names, df, X_normalized, top_n=10)

# Display recommendations
print(recommendations)
