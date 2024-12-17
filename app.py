import requests
import urllib.parse
import pandas as pd
import spotipy
import re
import numpy as np
import io
import base64

from datetime import datetime, timedelta
from flask import Flask, redirect, request, jsonify, session, render_template, url_for
from recommendation import preprocess_data, hybrid_recommendations
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
from scipy.spatial.distance import euclidean
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

app = Flask(__name__)
app.jinja_env.globals.update(zip=zip)
app.secret_key = '7Yb29#pLw*QfMv!Xt8J3zDk@5eH1Ua%'

CLIENT_ID = 'a1190d1d8dc44cc1a72e9cd795c11e4c'
CLIENT_SECRET = '3829a4cc7c0b4e20b6867402eae7d690'
REDIRECT_URI = 'http://localhost:5000/callback'

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))

# Load and preprocess the dataset
# dataset = preprocess_data(pd.read_csv('data/huggingface.csv'))

dataset = pd.read_csv('data/huggingface.csv')

artist_popularity = {} # Initialize dictionaries to store artist popularity and unique artists

# Preprocess dataset to extract unique artists and their popularity averages
for _, row in dataset.iterrows():
   artists = row['artists']
   popularity = row['popularity']

   if isinstance(artists, str):
      # Split artist names in case of collaborations
      artist_names = artists.split(';')
      for artist in artist_names:
         artist_name = artist.strip().lower()

         # Calculate the average popularity for each artist
         if artist_name not in artist_popularity:
               artist_popularity[artist_name] = {'popularity': 0, 'count': 0}
         
         artist_popularity[artist_name]['popularity'] += popularity
         artist_popularity[artist_name]['count'] += 1

# Compute the average popularity for each artist
for artist in artist_popularity:
   artist_popularity[artist] = artist_popularity[artist]['popularity'] / artist_popularity[artist]['count']

# Extract unique artist names
unique_artists = set(artist_popularity.keys())        

# Extract unique artist names
# unique_artists = dataset['artists'].unique()

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
   # if 'access_token' not in session:
   #    return redirect(url_for('login'))
   
   # if datetime.now().timestamp() > session['expires_at']:
   #    return redirect(url_for('refresh_token'))
   
   # headers = {
   #    'Authorization': f"Bearer {session['access_token']}"
   # }
   # response = requests.get(API_BASE_URL + 'me/top/tracks', headers=headers)

   # # Print the status code and response content for debugging
   # print("Response Status Code:", response.status_code)
   # print("Response JSON:", response.json())

   # response_data = response.json()
   # if 'items' in response_data:
   #    user_top_tracks = response_data['items']
   #    user_top_track_ids = [track['id'] for track in user_top_tracks]

   #    recommendations = hybrid_recommendations(user_top_track_ids, dataset)
   #    return render_template('recommend.html', recommendations=recommendations)
   # else:
   #    return jsonify({"error": "Failed to get top tracks. Please try again later."})
   
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
   if 'refresh_token' not in session:
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

   # Filter artists that match the query (case insensitive)
   matched_artists = [artist for artist in unique_artists if normalized_query in artist]

   # Retrieve the popularity for each matched artist
   matched_artists_info = []
   for artist in matched_artists:
      popularity = artist_popularity[artist]
      matched_artists_info.append({'name': artist, 'popularity': popularity})

   # Sort the artists by popularity
   sorted_artists = sorted(matched_artists_info, key=lambda x: x['popularity'], reverse=True)

   # Limit results to top 10 for efficiency
   return jsonify(sorted_artists[:10])

# def search_artists():
   # query = request.args.get('query', '')
   # if not query:
   #    return jsonify([])

   # # Normalize query by removing non-alphanumeric characters
   # normalized_query = re.sub(r'\W+', '', query.lower())

   # # Search for artists with a broader scope
   # search_result = sp.search(q=query, type='artist', limit=50)  # Use a general query instead of "artist:query"
   # artists = search_result['artists']['items']

   # matched_artists = []
   # seen_names = set()  # Set to keep track of unique artist names
   
   # for artist in artists:
   #    artist_name = artist['name']
   #    normalized_name = re.sub(r'\W+', '', artist_name.lower())
   #    match_score = fuzz.partial_ratio(normalized_query, normalized_name)
   #    if match_score < 80:
   #       alt_match_score = fuzz.partial_ratio(query.lower(), artist_name.lower())
   #       match_score = max(match_score, alt_match_score)
      
   #    # Check if the artist name is already seen
   #    if match_score >= 80 and artist_name.lower() not in seen_names:
   #       matched_artists.append((artist, match_score))
   #       seen_names.add(artist_name.lower())  # Add artist name to seen set to avoid duplicates

   # # Sort by match score and limit to top 10 results
   # sorted_artists = sorted(matched_artists, key=lambda x: x[1], reverse=True)
   # top_artists = [artist[0] for artist in sorted_artists[:10]]

   # return jsonify([{
   #    'name': artist['name'],
   #    'id': artist['id'],
   #    'popularity': artist['popularity']
   # } for artist in top_artists])



# Create a dictionary to store the feature data for each song
song_features = []

# Process the dataset and store song features
for _, row in dataset.iterrows():
   song = {
      'track_name': row['track_name'],
      'artists': row['artists'],
      'track_genre': row['track_genre'],
      'tempo': row['tempo'],
      'energy': row['energy'],
      'danceability': row['danceability'],
      'valence': row['valence'],
      'popularity': row['popularity'],
      'key': map_key_to_pitch(row['key'])
   }
   song_features.append(song)


def generate_user_profile(input_artists):
   user_profile = {
      'track_genre': [],
      'tempo': 0,
      'energy': 0,
      'danceability': 0,
      'valence': 0
   }

   # Iterate over each artist and extract their features
   for artist in input_artists:
      # Find all songs by the artist in the dataset
      artist_songs = dataset[dataset['artists'].str.contains(artist, case=False, na=False)]

      # Aggregate the features (average values for each feature)
      for _, song in artist_songs.iterrows():
         user_profile['track_genre'].extend(song['track_genre'])  # Assuming genres are comma-separated
         user_profile['tempo'] += song['tempo']
         user_profile['energy'] += song['energy']
         user_profile['danceability'] += song['danceability']
         user_profile['valence'] += song['valence']

      # Compute the average values for tempo, energy, danceability, and valence
      num_songs = len(artist_songs)
      user_profile['tempo'] /= num_songs
      user_profile['energy'] /= num_songs
      user_profile['danceability'] /= num_songs
      user_profile['valence'] /= num_songs            

      # Remove duplicate genres from user profile
      user_profile['track_genre'] = list(set(user_profile['track_genre']))

      return user_profile

def song_to_vector(song):
   # Combine genres (binary vector, presence/absence of genres)
   all_genres = ['acoustic', 'afrobeat', 'alt-rock', 'alternative', 'ambient', 'anime',
               'black-metal', 'bluegrass', 'blues', 'brazil', 'breakbeat', 'british',
               'cantopop', 'chicago-house', 'children', 'chill', 'classical', 'club', 'comedy',
               'country', 'dance', 'dancehall', 'death-metal', 'deep-house', 'detroit-techno',
               'disco', 'disney', 'drum-and-bass', 'dub', 'dubstep', 'edm', 'electro',
               'electronic', 'emo', 'folk', 'forro', 'french', 'funk', 'garage', 'german',
               'gospel', 'goth', 'grindcore', 'groove', 'grunge', 'guitar', 'happy',
               'hard-rock', 'hardcore', 'hardstyle', 'heavy-metal', 'hip-hop', 'honky-tonk',
               'house', 'idm', 'indian', 'indie-pop', 'indie', 'industrial', 'iranian',
               'j-dance', 'j-idol', 'j-pop', 'j-rock', 'jazz', 'k-pop', 'kids', 'latin',
               'latino', 'malay', 'mandopop', 'metal', 'metalcore', 'minimal-techno', 'mpb',
               'new-age', 'opera', 'pagode', 'party', 'piano', 'pop-film', 'pop', 'power-pop',
               'progressive-house', 'psych-rock', 'punk-rock', 'punk', 'r-n-b', 'reggae',
               'reggaeton', 'rock-n-roll', 'rock', 'rockabilly', 'romance', 'sad', 'salsa',
               'samba', 'sertanejo', 'show-tunes', 'singer-songwriter', 'ska', 'sleep',
               'songwriter', 'soul', 'spanish', 'study', 'swedish', 'synth-pop', 'tango',
               'techno', 'trance', 'trip-hop', 'turkish', 'world-music']
   genre_vector = [1 if genre in song['track_genre'] else 0 for genre in all_genres]

   # Create a vector with the remaining features
   features = [song['tempo'], song['energy'], song['danceability'], song['valence']]
   
   # Combine genre vector with numerical features
   return np.array(genre_vector + features) 

def get_recommended_songs(user_profile):
   # Convert user profile to a vector
   user_profile_vector = song_to_vector(user_profile)

   # Convert all songs in the dataset to vectors
   song_vectors = np.array([song_to_vector(song) for song in song_features])

   # Compute cosine similarity between user profile and each song in the dataset
   similarities = cosine_similarity(user_profile_vector.reshape(1, -1), song_vectors)

   # Sort the songs by similarity (highest first)
   sorted_similarities = similarities[0].argsort()[::-1]
   
   # Get the top N recommended songs (e.g., top 10)
   top_n = 10
   recommended_songs = [song_features[i] for i in sorted_similarities[:top_n]]

   # Add similarity score to each song's data for display
   for i, song in enumerate(recommended_songs):
      song['similarity_score'] = similarities[0][sorted_similarities[i]] * 100  # Convert to percentage
   
   return recommended_songs

@app.route('/new_user_recommendations', methods=['POST'])
def new_user():
   # Ensure the user is logged in
   if 'access_token' not in session:
      return jsonify({"error": "Please log in to use this feature"}), 401

   artist1 = request.form.get('artist1')
   artist2 = request.form.get('artist2')
   artist3 = request.form.get('artist3')

   input_artists = [artist1, artist2, artist3]
   user_profile = generate_user_profile(input_artists) # Generate user profile from the input artists
   print('USER PROFILE:', user_profile)
   recommended_songs = get_recommended_songs(user_profile) # Get recommendations based on the user profile
   print('RECOMMENDED SONGS:', recommended_songs)
   
   return render_template('new_user.html', recommendations=recommended_songs)

def map_key_to_pitch(key):
   key_mapping = {
      -1: "No key detected",
      0: "C",
      1: "C♯/D♭",
      2: "D",
      3: "D♯/E♭",
      4: "E",
      5: "F",
      6: "F♯/G♭",
      7: "G",
      8: "G♯/A♭",
      9: "A",
      10: "A♯/B♭",
      11: "B"
   }
   
   return key_mapping.get(key, "Invalid key")








   
def calculate_average_features(songs):
   average_features = {
      'tempo': 0,
      'energy': 0,
      'danceability': 0,
      'valence': 0
   }
   
   for song in songs: # Sum up all features
      average_features['tempo'] += song['tempo']
      average_features['energy'] += song['energy']
      average_features['danceability'] += song['danceability']
      average_features['valence'] += song['valence']

   for key in average_features: # Compute average for each feature
      average_features[key] /= len(songs)

   return average_features


def calculate_similarity(features1, features2):
   # Convert feature dictionaries into vectors
   vector1 = np.array([features1['tempo'], features1['energy'], features1['danceability'], features1['valence']])
   vector2 = np.array([features2['tempo'], features2['energy'], features2['danceability'], features2['valence']])
   
   # Normalize the vectors
   vector1 = vector1 / np.linalg.norm(vector1)
   vector2 = vector2 / np.linalg.norm(vector2)
   
   # Compute cosine similarity
   similarity = np.dot(vector1, vector2)
   return similarity


def plot_radar_chart_image(artist_features, recommended_features):
   categories = ['tempo', 'energy', 'danceability', 'valence']
   num_categories = len(categories)

   artist_values = [artist_features[feature] for feature in categories]
   recommended_values = [recommended_features[feature] for feature in categories]

   artist_values += artist_values[:1]
   recommended_values += recommended_values[:1]
   
   angles = np.linspace(0, 2 * np.pi, num_categories, endpoint=False).tolist()
   angles += angles[:1]

   fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
   ax.fill(angles, artist_values, color='blue', alpha=0.25, label='Input Artists')
   ax.fill(angles, recommended_values, color='red', alpha=0.25, label='Recommended Songs')
   ax.set_yticks([])
   ax.set_xticks(angles[:-1])
   ax.set_xticklabels(categories)
   ax.legend(loc='upper right', bbox_to_anchor=(1.1, 1.1))

   canvas = FigureCanvas(fig)
   img = io.BytesIO()
   canvas.print_png(img)
   img.seek(0)
   img_data = base64.b64encode(img.read()).decode('utf-8')

   return img_data


def compare_statistics(input_artists, recommended_songs):
   # Get all songs for the input artists
   artist_songs = []
   for artist in input_artists:
      artist_songs.extend(dataset[dataset['artists'].str.contains(artist, case=False, na=False)].to_dict('records'))
   
   # Calculate average features for input artists and recommended songs
   artist_features = calculate_average_features(artist_songs)
   recommended_features = calculate_average_features(recommended_songs)
   
   # Calculate similarity
   similarity_score = calculate_similarity(artist_features, recommended_features)
   
   # Plot radar chart
   plot_radar_chart(artist_features, recommended_features, title=f"Feature Similarity: {similarity_score:.2f}")
   
   return similarity_score


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