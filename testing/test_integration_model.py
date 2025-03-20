# Uses real data to test the recommendation pipeline

import pytest
import sys
import os
import pandas as pd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from model import recommend_songs, evaluate_model, df

# Suppress Sklearn warnings globally
pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")

TEST_ARTIST = "Aespa".lower()  # artist in dataset
FAKE_ARTIST = "Unknown Artist 123" # artise not in dataset


### Test if recommend_songs returns valid results for an existing artist
def test_recommend_songs_valid_artist():
   recommended_songs = recommend_songs(TEST_ARTIST, num_songs=5)
   
   # Check if recommendations are returned
   assert recommended_songs is not None, "recommend_songs should return a DataFrame, not None"
   
   # Check if correct columns are present
   expected_columns = {'track_name', 'artists', 'track_genre', 'cosine_similarity', 
                     'final_score', 'key', 'tempo', 'danceability', 'acousticness', 
                     'valence', 'energy', 'popularity', 'mode', 'loudness', 'time_signature'}
   assert set(recommended_songs.columns) == expected_columns, "Returned DataFrame has incorrect columns"

   # Check if values are within expected ranges
   assert recommended_songs['danceability'].between(0, 1).all(), "Danceability values should be between 0 and 1"
   assert recommended_songs['energy'].between(0, 1).all(), "Energy values should be between 0 and 1"
   assert recommended_songs['valence'].between(0, 1).all(), "Valence values should be between 0 and 1"
   assert recommended_songs['final_score'].between(0, 1).all(), "Final scores should be between 0 and 1"


### Test if recommend_songs returns None for an artist not in the dataset
def test_recommend_songs_invalid_artist():
   recommended_songs, message = recommend_songs(FAKE_ARTIST, num_songs=5)
   assert recommended_songs is None, "Should return None if artist is not found"
   assert message == "Artist not found in the dataset.", "Incorrect error message for unknown artist"


### Test if evaluate_model returns expected metrics
def test_evaluate_model():
   recommended_songs = recommend_songs(TEST_ARTIST, num_songs=10)
   
   # Check evaluation results
   eval_results = evaluate_model(recommended_songs, input_genre=recommended_songs.iloc[0]['track_genre'])

   assert isinstance(eval_results, dict), "evaluate_model should return a dictionary"
   assert "Mean Cosine Similarity" in eval_results, "Missing 'Mean Cosine Similarity' metric"
   assert "Precision@10" in eval_results, "Missing 'Precision@10' metric"
   assert "NDCG" in eval_results, "Missing 'NDCG' metric"
   assert "Diversity" in eval_results, "Missing 'Diversity' metric"

   # Check metric value ranges
   assert 0 <= eval_results["Mean Cosine Similarity"] <= 1, "Mean Cosine Similarity should be between 0 and 1"
   assert 0 <= eval_results["Precision@10"] <= 1, "Precision@10 should be between 0 and 1"
   assert 0 <= eval_results["NDCG"] <= 1, "NDCG should be between 0 and 1"
   assert eval_results["Diversity"] >= 0, "Diversity should be non-negative"
   