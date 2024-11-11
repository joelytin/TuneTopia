import requests
import urllib.parse
import pandas as pd
import spotipy
import re

from datetime import datetime, timedelta
from flask import Flask, redirect, request, jsonify, session, render_template, url_for
from recommendation import preprocess_data, hybrid_recommendations
from spotipy.oauth2 import SpotifyClientCredentials
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

app = Flask(__name__)
app.secret_key = '7Yb29#pLw*QfMv!Xt8J3zDk@5eH1Ua%'

CLIENT_ID = 'c4ccf9590da446f591e8d6520db66971'
CLIENT_SECRET = '945eadb35b8a494b9740c1a64cf55c19'
REDIRECT_URI = 'http://localhost:5000/callback'

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))

# Load and preprocess the dataset
dataset = preprocess_data(pd.read_csv('data/huggingface.csv'))

@app.route('/')
def index():
   if 'access_token' in session:
      return redirect(url_for('home'))
   return render_template('index.html')

@app.route('/test')
def test():
   return render_template('test.html')

@app.route('/home')
def home():
   return render_template('home.html')

@app.route('/about')
def about():
   return render_template('about.html')

# @app.route('/recommend')
# def recommend():
   if 'access_token' not in session:
      return redirect(url_for('login'))
   
   if datetime.now().timestamp() > session['expires_at']:
      return redirect(url_for('refresh_token'))
   
   headers = {
      'Authorization': f"Bearer {session['access_token']}"
   }
   response = requests.get(API_BASE_URL + 'me/top/tracks', headers=headers)

   # Print the status code and response content for debugging
   print("Response Status Code:", response.status_code)
   print("Response JSON:", response.json())

   response_data = response.json()
   if 'items' in response_data:
      user_top_tracks = response_data['items']
      user_top_track_ids = [track['id'] for track in user_top_tracks]

      recommendations = hybrid_recommendations(user_top_track_ids, dataset)
      return render_template('recommend.html', recommendations=recommendations)
   else:
      return jsonify({"error": "Failed to get top tracks. Please try again later."})
   
@app.route('/recommend')
def recommend():
   return render_template('recommend.html')

@app.route('/metronome')
def metronome():
   return render_template('metronome.html')

@app.route('/login')
def login():
   scope = 'user-read-private user-read-email user-library-read user-top-read'
   params = {
      'client_id': CLIENT_ID,
      'response_type': 'code',
      'scope': scope,
      'redirect_uri': REDIRECT_URI,
      'show_dialog': True # set to False after testing
   }

   auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
   return redirect(auth_url)

@app.route('/callback')
def callback():
   if 'error' in request.args:
      return jsonify({"error": request.args['error']})
   
   # Login successful
   if 'code' in request.args:
      # Build request body with data to be sent to Spotify to get access token
      req_body = {
         'code': request.args['code'],
         'grant_type': 'authorization_code',
         'redirect_uri': REDIRECT_URI,
         'client_id': CLIENT_ID,
         'client_secret': CLIENT_SECRET
      }

      response = requests.post(TOKEN_URL, data=req_body)
      token_info = response.json()

      session['access_token'] = token_info['access_token']
      session['refresh_token'] = token_info['refresh_token']
      session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']
      # Access token only lasts for 1 day

      # Fetch user profile
      user_profile = requests.get(API_BASE_URL + 'me', headers={'Authorization': f"Bearer {token_info['access_token']}"})
      user_info = user_profile.json()

      # Store additional user profile data in session
      session['user_name'] = user_info['display_name']
      session['user_id'] = user_info['id']
      session['user_email'] = user_info['email']
      session['user_uri'] = user_info['uri']
      session['user_link'] = user_info['external_urls']['spotify']
      session['user_image'] = user_info['images'][0]['url'] if user_info.get('images') else None

      return redirect(url_for('home'))
   
# Refresh token
@app.route('/refresh-token')
def refresh_token():
   # Check if refresh token is NOT in the session, redirect to login
   if 'refresh-token' not in session:
      return redirect(url_for('login'))
   
   # If access token is expired, make a request to get a fresh one
   if datetime.now().timestamp() > session['expires_at']:
      req_body = {
         'grant_type': 'refresh_token',
         'refresh_token': session['refresh_token'],
         'client_id': CLIENT_ID,
         'client_secret': CLIENT_SECRET
      }
   
      response = requests.post(TOKEN_URL, data=req_body)
      new_token_info = response.json()

      # Override the access token we had before
      session['access_token'] = new_token_info['access_token']
      session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']

      return redirect(url_for('recommend'))
   
@app.route('/logout')
def logout():
   session.clear()
   return redirect(url_for('index'))

@app.route('/new-user-form')
def new_user_form():
   return render_template('new_user.html')

@app.route('/search_artists')
def search_artists():
   query = request.args.get('query', '')
   if not query:
      return jsonify([])

   # Normalize query by removing non-alphanumeric characters
   normalized_query = re.sub(r'\W+', '', query.lower())

   # Search for artists with a broader scope
   search_result = sp.search(q=query, type='artist', limit=50)  # Use a general query instead of "artist:query"
   artists = search_result['artists']['items']

   matched_artists = []
   seen_names = set()  # Set to keep track of unique artist names
   
   for artist in artists:
      artist_name = artist['name']
      normalized_name = re.sub(r'\W+', '', artist_name.lower())
      match_score = fuzz.partial_ratio(normalized_query, normalized_name)
      if match_score < 80:
         alt_match_score = fuzz.partial_ratio(query.lower(), artist_name.lower())
         match_score = max(match_score, alt_match_score)
      
      # Check if the artist name is already seen
      if match_score >= 80 and artist_name.lower() not in seen_names:
         matched_artists.append((artist, match_score))
         seen_names.add(artist_name.lower())  # Add artist name to seen set to avoid duplicates

   # Sort by match score and limit to top 10 results
   sorted_artists = sorted(matched_artists, key=lambda x: x[1], reverse=True)
   top_artists = [artist[0] for artist in sorted_artists[:10]]

   return jsonify([{
      'name': artist['name'],
      'id': artist['id'],
      'popularity': artist['popularity']
   } for artist in top_artists])

def clamp(value, min_value, max_value):
    return max(min(value, max_value), min_value)

@app.route('/new_user_recommendations', methods=['POST'])
def new_user_recommendations():
   # Get artist names from the form
   artist1 = request.form.get('artist1')
   artist2 = request.form.get('artist2')
   artist3 = request.form.get('artist3')
   artist_names = [artist1, artist2, artist3]

   audio_features_data = []

   # Step 1: Collect audio features from top tracks for each artist
   for artist_name in artist_names:
      try:
         # Fetch artist's Spotify ID
         search_result = sp.search(f'artist:"{artist_name}"', type='artist', limit=1)
         if search_result['artists']['items']:
               artist_info = search_result['artists']['items'][0]
               top_tracks = sp.artist_top_tracks(artist_info['id'], country='US')['tracks']
               track_ids = [track['id'] for track in top_tracks]

               # Fetch audio features for these tracks
               audio_features = sp.audio_features(track_ids)
               audio_features_data.extend([feat for feat in audio_features if feat])
      except Exception as e:
         return jsonify({"error": f"Error processing artist '{artist_name}': {str(e)}"})

   if not audio_features_data:
      return jsonify({"error": "No audio features found for the input artists."})

   # Step 2: Average the audio features
   features = ['danceability', 'energy', 'loudness', 'speechiness', 'acousticness',
               'instrumentalness', 'liveness', 'valence', 'tempo']
   user_profile = pd.DataFrame(audio_features_data)[features].mean().to_dict()

   # Step 3: Clamp values to ensure they fall within Spotify's acceptable ranges
   user_profile['danceability'] = clamp(user_profile['danceability'], 0.0, 1.0)
   user_profile['energy'] = clamp(user_profile['energy'], 0.0, 1.0)
   user_profile['loudness'] = clamp(user_profile['loudness'], -60.0, 0.0)
   user_profile['speechiness'] = clamp(user_profile['speechiness'], 0.0, 1.0)
   user_profile['acousticness'] = clamp(user_profile['acousticness'], 0.0, 1.0)
   user_profile['instrumentalness'] = clamp(user_profile['instrumentalness'], 0.0, 1.0)
   user_profile['liveness'] = clamp(user_profile['liveness'], 0.0, 1.0)
   user_profile['valence'] = clamp(user_profile['valence'], 0.0, 1.0)
   user_profile['tempo'] = clamp(user_profile['tempo'], 0.0, 250.0)

   # Step 4: Request Spotify recommendations based on the averaged audio features
   try:
      recommendations = sp.recommendations(
         limit=10,
         target_danceability=user_profile['danceability'],
         target_energy=user_profile['energy'],
         target_loudness=user_profile['loudness'],
         target_speechiness=user_profile['speechiness'],
         target_acousticness=user_profile['acousticness'],
         target_instrumentalness=user_profile['instrumentalness'],
         target_liveness=user_profile['liveness'],
         target_valence=user_profile['valence'],
         target_tempo=user_profile['tempo']
      )

      # Step 5: Prepare recommendations for display
      recommended_tracks = [{
         'track_name': track['name'],
         'artists': ', '.join(artist['name'] for artist in track['artists']),
         'album_name': track['album']['name'],
         'popularity': track['popularity'],
         'preview_url': track['preview_url']
      } for track in recommendations['tracks']]

      return render_template('new_user.html', recommendations=recommended_tracks)

   except Exception as e:
      return jsonify({"error": f"Error fetching recommendations: {str(e)}"})

   
   # artist1 = request.form['artist1']
   # artist2 = request.form['artist2']
   # artist3 = request.form['artist3']

   # if 'access_token' not in session:
   #    return redirect(url_for('login'))
   
   # if datetime.now().timestamp() > session['expires_at']:
   #    return redirect(url_for('refresh_token'))

   # headers = {
   #    'Authorization': f"Bearer {session['access_token']}"
   # }
   
   # user_top_tracks = get_top_tracks_for_artists([artist1, artist2, artist3])
   # user_top_track_ids = [track['id'] for track in user_top_tracks]

   # recommendations = hybrid_recommendations(user_top_track_ids, dataset)
   # return render_template('new_user.html', recommendations=recommendations)

    
def get_top_tracks_for_artists(artists):
   if 'access_token' not in session or datetime.now().timestamp() > session.get('expires_at', 0):
      # Redirect to refresh token if expired or missing
      redirect(url_for('refresh_token'))
   
   top_tracks = []

   headers = {
      'Authorization': f"Bearer {session['access_token']}"
   }

   for artist in artists:
      response = requests.get(API_BASE_URL + f'search?q={artist}&type=artist', headers=headers)
      result = response.json()

      # Check if 'artists' and 'items' exist in the response
      if 'artists' in result and 'items' in result['artists']:
         if result['artists']['items']:
            artist_id = result['artists']['items'][0]['id']
            tracks_response = requests.get(API_BASE_URL + f'artists/{artist_id}/top-tracks?country=US', headers=headers)
            tracks_result = tracks_response.json()

            # Check if 'tracks' exists in the tracks_result
            if 'tracks' in tracks_result:
               top_tracks.extend(tracks_result['tracks'])
         else:
            print(f"No items found for artist: {artist}")
      else:
         print(f"Unexpected response format for artist search: {result}")
         
   return top_tracks


# Run Flask server
if __name__ == '__main__':
   app.run(host='0.0.0.0', debug=True)