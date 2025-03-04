import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA # Principal Component Analysis. To simplify complex data by reducing its features (cols) while keeping the most important info.
from sklearn.metrics import ndcg_score
from scipy.stats import entropy
import joblib

df = pd.read_csv("data/huggingface.csv")

# Select features
features = ['danceability', 'energy', 'valence', 'speechiness', 'acousticness', 'instrumentalness', 'liveness']

# Normalize feature values
scaler = StandardScaler()
df[features] = scaler.fit_transform(df[features])

# Handle missing genre values
df['track_genre'] = df['track_genre'].fillna('')

# Use TF-IDF to create genre embeddings
vectorizer = TfidfVectorizer()
genres = df['track_genre'].unique()
genre_embeddings = vectorizer.fit_transform(genres)  # Convert genres to vectors

# Store embeddings as dense NumPy arrays
genre_embedding_dict = {genre: vector.toarray().flatten() for genre, vector in zip(genres, genre_embeddings)}

# Compute genre similarity
def compute_genre_weight(genre1, genre2):
   if genre1 not in genre_embedding_dict or genre2 not in genre_embedding_dict:
      return 0  # If missing, assign similarity of 0
   return cosine_similarity(genre_embedding_dict[genre1].reshape(1, -1),
                           genre_embedding_dict[genre2].reshape(1, -1))[0][0]

# Reduce feature space using PCA to remove redundancy
pca = PCA(n_components=5) # Reduce to 5 key components
df_pca = pca.fit_transform(df[features]) # Transform dataset features
df_pca = pd.DataFrame(df_pca, index=df.index) # Convert back to DataFrame

# Define musical key mapping
key_mapping = {
   -1: "No key detected",
   0: "C", 1: "C♯/D♭", 2: "D", 3: "D♯/E♭", 4: "E", 5: "F",
   6: "F♯/G♭", 7: "G", 8: "G♯/A♭", 9: "A", 10: "A♯/B♭", 11: "B"
}

def recommend_songs(artist_name, df=df, features=features, num_songs=15, alpha=0.7):
   artist_songs = df[df['artists'].str.contains(artist_name, case=False, na=False)]
   if artist_songs.empty:
      return None, "Artist not found in the dataset."

   reference_vector = pca.transform(artist_songs[features]).mean(axis=0).reshape(1, -1)
   df['cosine_similarity'] = cosine_similarity(reference_vector, df_pca)[0]

   input_genre = artist_songs.iloc[0]['track_genre']
   df['genre_weight'] = df['track_genre'].apply(lambda x: compute_genre_weight(input_genre, x))

   # Add weighting factor for key/tempo similarity as some users might want harmonically compatible recommendations
   df['key_similarity'] = (df['key'] == artist_songs.iloc[0]['key']).astype(int)

   # Weighted similarity score
   df['final_score'] = (alpha * df['cosine_similarity']) + \
                     ((1 - alpha) * df['genre_weight']) + \
                     (0.1 * df['key_similarity'])

   df['final_score'] = (df['final_score'] - df['final_score'].min()) / \
                     (df['final_score'].max() - df['final_score'].min()) # Ensure final_score is between 0-1

   # Sort by final score
   recommended_songs = df[df['artists'].str.lower() != artist_name.lower()].sort_values(by='final_score', ascending=False)

   # Remove duplicate track names, keeping the one with the highest score
   recommended_songs = recommended_songs.drop_duplicates(subset=["track_name", "artists"])

   recommended_songs['key'] = recommended_songs['key'].map(key_mapping) # Map numeric key values to musical notes

   recommended_songs = recommended_songs.head(num_songs).copy()  # Copy only necessary rows
   recommended_songs['artists'] = recommended_songs['artists'].astype(str)  # Convert only required rows

   return recommended_songs[['track_name', 'artists', 'track_genre', 'cosine_similarity', 
                          'final_score', 'key', 'tempo', 'danceability', 'acousticness', 
                          'valence', 'energy', 'popularity', 'mode', 'loudness', 'time_signature']]

def evaluate_model(recommended_songs, input_genre, num_songs=15):
   mean_cosine_similarity = recommended_songs['cosine_similarity'].mean()
   precision_at_10 = (recommended_songs['track_genre'] == input_genre).sum() / num_songs
   total_relevant_items = df[df['track_genre'] == input_genre].shape[0]
   relevance_scores = (recommended_songs['track_genre'] == input_genre).astype(int)
   ndcg = ndcg_score([relevance_scores], [recommended_songs['final_score']])

   genre_counts = recommended_songs['track_genre'].value_counts()
   diversity = entropy(genre_counts) # Using Shannon Entropy (more accurate measure of diversity)

   return {
      "Mean Cosine Similarity": mean_cosine_similarity,
      "Precision@10": precision_at_10,
      "NDCG": ndcg,
      "Diversity": diversity,
      "Recommended Songs": recommended_songs[['track_name', 'artists', 'track_genre', 'final_score', 'key', 'tempo', 'danceability', 'acousticness']]
   }