import pytest
import os
import sys
import warnings
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app  # Import your Flask app
from model import df
from flask import json

# Suppress Sklearn warnings globally
pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")

# Fixture to set up a test client for Flask app
@pytest.fixture
def client():
   app.config["TESTING"] = True
   with app.test_client() as client:
      yield client

# ---------------------- 1️⃣ UNIT TESTING ---------------------- #
"""Test recommend_songs is called with correct parameters"""
def test_recommend_songs_mock(mocker):
   # Ensure correct patching path (since it's imported directly in app.py)
   mock_recommend = mocker.patch("app.recommend_songs", return_value="mocked_response")

   artist_name = "aespa"
   num_songs = 5
   alpha = 0.5

   with app.test_client() as client:
      client.post("/recommend", data={"artist": artist_name, "alpha": alpha, "num_songs": num_songs})

   # Ensure mock was used
   mock_recommend.assert_called_once_with(artist_name, df, num_songs=num_songs, alpha=alpha)


# ---------------------- 2️⃣ ROUTE TESTING ---------------------- #
"""Test if the home page loads successfully"""
def test_home_page(client):
   response = client.get("/")
   assert response.status_code == 200
   assert b"Home page loaded" in response.data

"""Test if the recommend page loads successfully"""
def test_recommend_page(client):
   response = client.get("/recommend")
   assert response.status_code == 200
   assert b"Recommend page loaded" in response.data

"""Test for 404 error on a non-existent page."""
def test_non_existent_page(client):
   response = client.get("/nonexistent")
   assert response.status_code == 404


# ---------------------- 3️⃣ API TESTING ---------------------- #
"""Test if /search_artists API returns valid JSON response"""
def test_search_artists_api(client):
   response = client.get("/search_artists?query=aespa")
   assert response.status_code == 200
   data = json.loads(response.data)
   assert isinstance(data, list)  # API should return a list of artists
   assert "name" in data[0]  # Each artist object should contain 'name'


# ---------------------- 4️⃣ FUNCTIONAL TESTING ---------------------- #
"""Test full recommendation workflow with valid input"""
def test_recommend_functionality(client):
   response = client.post("/recommend", data={"artist": "aespa", "alpha": 0.5, "num_songs": 5})
   
   assert response.status_code == 200


# ---------------------- 5️⃣ ERROR HANDLING TESTING ---------------------- #
"""Test recommendation when user submits empty input"""
def test_recommend_empty_input(client):
   response = client.post("/recommend", data={"artist": ""})
   
   assert response.status_code == 200

"""Test for invalid values of alpha and num_songs"""
@pytest.mark.parametrize("alpha, num_songs", [(-1, 5), (1.5, 5), (0.5, 50), ("invalid", "invalid")])
def test_recommend_invalid_values(client, alpha, num_songs):
   response = client.post("/recommend", data={"artist": "aespa", "alpha": alpha, "num_songs": num_songs})
   assert response.status_code == 200
   assert b'id="error-indicator"' in response.data

"""Test recommendation when artist is not found"""
def test_recommend_artist_not_found(client):
   response = client.post("/recommend", data={"artist": "NonExistentArtist", "alpha": "0.5", "num_songs": "5"})
   assert response.status_code == 200
   assert b'Artist not found in the dataset.' in response.data  # Adjust to match actual error message
