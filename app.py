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

@app.route('/new_user_recommendations', methods=['POST'])
def new_user_recommendations():
   artist1 = request.form.get('artist1')
   artist2 = request.form.get('artist2')
   artist3 = request.form.get('artist3')

   artist_data = []
   for artist_name in [artist1, artist2, artist3]:
      try:
         search_result = sp.search(f'artist:"{artist_name}"', type='artist', limit=5)  # Increased limit for more results
         if search_result['artists']['items']:
            print(f"Search results for artist '{artist_name}':", search_result['artists']['items'])  # Debugging line

            # Check for exact name match to avoid similar-sounding results
            exact_match_found = False
            for item in search_result['artists']['items']:
               print(f"Checking artist name: {item['name']} (input: {artist_name})")  # Debugging line
               if item['name'].lower() == artist_name.lower():  # Compare lowercase to handle case insensitivity
                  artist_info = item
                  artist_data.append({
                     'name': artist_info['name'],
                     'id': artist_info['id'],
                     'genres': artist_info['genres'],
                     'popularity': artist_info['popularity'],
                     'uri': artist_info['uri'],
                     'type': artist_info['type']
                  })
                  exact_match_found = True
                  break

            if not exact_match_found:
               return jsonify({"error": f"No exact match found for artist '{artist_name}'."})

         else:
            return jsonify({"error": f"Artist '{artist_name}' not found."})

      except Exception as e:
         return jsonify({"error": f"Error searching for artist '{artist_name}': {str(e)}"})

   
   print("Artist Data Retrieved:", artist_data)
   
   track_data = []
   track_ids = []
   for artist in artist_data:
      try:
         top_tracks_response = sp.artist_top_tracks(artist['id'], country='US')
         top_tracks = top_tracks_response['tracks']

         # Extract relevant track details
         for track in top_tracks:
            track_data.append({
               'artist_name': artist['name'],
               'track_name': track['name'],
               'album_name': track['album']['name'],
               'track_id': track['id'],
               'popularity': track['popularity'],
            })
            track_ids.append(track['id'])
      except Exception as e:
         return jsonify({"error": f"Error fetching top tracks for artist '{artist['name']}': {str(e)}"})
   
   print("Track Data Retrieved:", track_data)
   
   audio_features_data = []
   try:
      audio_features_response = sp.audio_features(track_ids)
      for features in audio_features_response:
         if features: # Ensure features are available
            audio_features_data.append({
               'track_id': features['id'],
               'danceability': features['danceability'],
               'energy': features['energy'],
               'key': features['key'],
               'loudness': features['loudness'],
               'mode': features['mode'],
               'speechiness': features['speechiness'],
               'acousticness': features['acousticness'],
               'instrumentalness': features['instrumentalness'],
               'liveness': features['liveness'],
               'valence': features['valence'],
               'tempo': features['tempo'],
               'time_signature': features['time_signature'],
            })
   except Exception as e:
      return jsonify({"error": f"Error fetching audio features for tracks: {str(e)}"})
   
   # print("Audio Features Retrieved:", audio_features_data)
   # return jsonify({"artist_data": artist_data, "track_data": track_data, "audio_features_data": audio_features_data})

   # Combine track data and audio features by track ID
   for track in track_data:
      for features in audio_features_data:
         if track['track_id'] == features['track_id']:
               track.update(features)

   print("Track Data with Audio Features:", track_data)
   return jsonify(track_data)  # Temporary for testing purposes
   
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