# Tests recommend_songs() in isolation with a mocked dataset

import pytest
import sys
import os
import pandas as pd
from unittest.mock import patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import model
from model import recommend_songs

# Suppress Sklearn warnings globally
pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")

# Mock dataset with multiple songs per artist and varied keys
mock_df = pd.DataFrame({
   "track_name": ["Girls", "Falling in Love", "I'm Yours", "Next Level", "strawberry lipstick"],
   "artists": ["aespa", "Landon Pigg", "Jason Mraz", "aespa", "YUNGBLUD"],  # aespa has 2 songs
   "track_genre": ["pop", "rock", "pop", "pop", "alternative"],
   "danceability": [0.8, 0.5, 0.7, 0.85, 0.6],
   "energy": [0.9, 0.4, 0.8, 0.95, 0.5],
   "valence": [0.6, 0.3, 0.5, 0.7, 0.4],
   "speechiness": [0.1, 0.05, 0.07, 0.12, 0.08],
   "acousticness": [0.2, 0.8, 0.3, 0.15, 0.7],
   "instrumentalness": [0.0, 0.6, 0.1, 0.02, 0.5],
   "liveness": [0.3, 0.2, 0.4, 0.35, 0.25],
   "key": [1, 5, 1, 1, 5],  # aespa songs have the same key
   "tempo": [120, 90, 110, 125, 80],
   "popularity": [80, 50, 75, 85, 60],
   "mode": [1, 0, 1, 1, 0],
   "loudness": [-5, -10, -6, -4, -9],
   "time_signature": [4, 4, 4, 4, 4],
})


### Patch `df` with a small mock dataset for unit testing
@pytest.fixture
def mock_data():
   original_df = model.df.copy()  # Backup original dataset
   model.df = mock_df  # Replace with mock dataset
   yield
   model.df = original_df  # Restore after test


### Test recommendations for a valid artist
def test_recommend_songs_valid_artist(mock_data):
   artist = "aespa"
   recommended_songs = recommend_songs(artist, num_songs=2)

   assert isinstance(recommended_songs, pd.DataFrame), "Expected DataFrame output"
   assert len(recommended_songs) == 2, "Should return 2 recommendations"
   assert "track_name" in recommended_songs.columns, "Missing 'track_name' column"
   assert "final_score" in recommended_songs.columns, "Missing 'final_score' column"
   assert not any(recommended_songs["artists"].str.contains(artist)), "Should not recommend the same artist"

   
### Test behavior when artist is not found
def test_recommend_songs_invalid_artist(mock_data):
   artist = "Nonexistent Artist"
   recommended_songs, error_message = recommend_songs(artist, num_songs=2)

   assert recommended_songs is None, "Should return None when artist not found"
   assert error_message == "Artist not found in the dataset.", "Expected 'Artist not found' error message"


### Test when an artist has multiple songs
def test_recommend_songs_multiple_songs(mock_data):
   artist = "aespa"  # This artist has 2 songs
   recommended_songs = recommend_songs(artist, num_songs=2)

   assert isinstance(recommended_songs, pd.DataFrame), "Expected DataFrame output"
   assert len(recommended_songs) == 2, "Should return 2 recommendations"
   assert not any(recommended_songs["artists"].str.contains(artist)), "Should exclude input artist"


### Ensure genre similarity influences recommendations
def test_recommend_songs_genre_weighting(mock_data):
   artist = "aespa"
   recommended_songs = recommend_songs(artist, num_songs=5)

   # Since aespa is pop, at least one pop song should be recommended
   assert any(recommended_songs["track_genre"] == "pop"), "Should recommend songs in the same genre"


### Ensure alpha affects ranking of recommendations
def test_recommend_songs_alpha_impact(mock_data):
   artist = "aespa"

   # Get recommendations with high alpha (prioritise cosine similarity)
   high_alpha_recommendations = recommend_songs(artist, num_songs=5, alpha=0.9)

   # Get recommendations with low alpha (prioritise genre similarity)
   low_alpha_recommendations = recommend_songs(artist, num_songs=5, alpha=0.1)

   # Ensure rankings change when alpha changes
   assert not high_alpha_recommendations.equals(low_alpha_recommendations), "Changing alpha should affect rankings"
