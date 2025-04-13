import pandas as pd
import numpy as np
import tracemalloc
import joblib
import psutil
import os
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA # Principal Component Analysis. To simplify complex data by reducing its features (cols) while keeping the most important info.
from sklearn.metrics import ndcg_score
from scipy.stats import entropy

tracemalloc.start()

df = pd.read_csv("data/huggingface.csv", low_memory=False)

# Select features
features = ['danceability', 'energy', 'valence', 'speechiness', 'acousticness', 'instrumentalness', 'liveness']

# Normalize feature values
scaler = StandardScaler()
df[features] = scaler.fit_transform(df[features])

# Handle missing genre values
df.fillna({'track_genre': ''}, inplace=True)

# Use TF-IDF to create genre embeddings
vectorizer = TfidfVectorizer()
genre_embeddings = vectorizer.fit_transform(df['track_genre'])
genre_embedding_array = genre_embeddings.toarray()  # Convert to dense NumPy array

# Load or compute PCA
if os.path.exists("data/df_pca.npy") and os.path.exists("data/pca_model.pkl"):
   df_pca = np.load("data/df_pca.npy")
   pca = joblib.load("data/pca_model.pkl")
else:
   pca = PCA(n_components=5)
   df_pca = pca.fit_transform(df[features])
   np.save("data/df_pca.npy", df_pca)
   joblib.dump(pca, "data/pca_model.pkl")

process = psutil.Process(os.getpid())
mem = process.memory_info().rss / (1024 * 1024)  # in MB
print(f"Memory usage: {mem:.2f} MB")

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

   # Compute reference vector (avg PCA values)
   reference_vector = pca.transform(artist_songs[features].to_numpy()).mean(axis=0, keepdims=True) 
   # Compute cosine similarity in one step
   cosine_similarities = cosine_similarity(reference_vector, df_pca)[0]

   # Compute genre similarity efficiently
   input_genre_vector = vectorizer.transform([artist_songs.iloc[0]['track_genre']]).toarray()
   genre_similarities = cosine_similarity(input_genre_vector, genre_embedding_array)[0]

   # Compute key similarity
   input_key = artist_songs.iloc[0]['key']
   key_similarities = (df['key'].to_numpy() == input_key).astype(int)
   
   final_scores = (alpha * cosine_similarities) + \
                  ((1 - alpha) * genre_similarities) + \
                  (0.1 * key_similarities)

   # Normalize scores to range 0-1
   final_scores = (final_scores - final_scores.min()) / (final_scores.max() - final_scores.min())

   # Store results in DataFrame for sorting
   df_copy = df.copy()
   df_copy['final_score'] = final_scores
   df_copy['cosine_similarity'] = cosine_similarities
   df_copy['genre_weight'] = genre_similarities
   df_copy['key_similarity'] = key_similarities

   # Inverse transform features (still safe since df_copy is local)
   df_copy[features] = scaler.inverse_transform(df_copy[features])

   # Filter out original artist's songs and remove duplicates
   recommended_songs = df_copy.query('artists.str.lower() != @artist_name.lower()').sort_values('final_score', ascending=False)
   recommended_songs = recommended_songs.drop_duplicates(subset=["track_name", "artists"])
   recommended_songs['key'] = recommended_songs['key'].map(key_mapping)

   return recommended_songs.head(num_songs)[['track_name', 'artists', 'track_genre', 'cosine_similarity',
                                             'final_score', 'key', 'tempo', 'danceability', 'acousticness',
                                             'valence', 'energy', 'popularity', 'mode', 'loudness', 
                                             'time_signature', 'youtube_url']]

current, peak = tracemalloc.get_traced_memory()
print(f"Current memory usage: {current / 1024 / 1024:.2f} MB")
print(f"Peak memory usage: {peak / 1024 / 1024:.2f} MB")
tracemalloc.stop()

def evaluate_model(recommended_songs, input_genre, num_songs=15):
   mean_cosine_similarity = recommended_songs['cosine_similarity'].mean()
   precision_at_10 = (recommended_songs['track_genre'] == input_genre).sum() / num_songs
   
   relevance_scores = (recommended_songs['track_genre'] == input_genre).astype(int)
   ndcg = ndcg_score([relevance_scores], [recommended_songs['final_score']])

   genre_counts = recommended_songs['track_genre'].value_counts()
   diversity = entropy(genre_counts) # Using Shannon Entropy (more accurate measure of diversity)

   return {
      "Mean Cosine Similarity": mean_cosine_similarity,
      "Precision@10": precision_at_10,
      "NDCG": ndcg,
      "Diversity": diversity,
      "Recommended Songs": recommended_songs[['track_name', 'artists', 'track_genre', 'final_score',
                                              'key', 'tempo', 'danceability', 'acousticness']]
   }