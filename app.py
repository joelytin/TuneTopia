import requests
import urllib.parse
import pandas as pd

from datetime import datetime, timedelta
from flask import Flask, redirect, request, jsonify, session, render_template, url_for
from recommendation import preprocess_data, hybrid_recommendations


app = Flask(__name__)
app.secret_key = '7Yb29#pLw*QfMv!Xt8J3zDk@5eH1Ua%'

CLIENT_ID = 'c4ccf9590da446f591e8d6520db66971'
CLIENT_SECRET = '945eadb35b8a494b9740c1a64cf55c19'
REDIRECT_URI = 'http://localhost:5000/callback'

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'

# Load and preprocess the dataset
dataset = preprocess_data(pd.read_csv('data/huggingface.csv'))

@app.route('/')
def index():
   if 'access_token' in session:
      return redirect(url_for('home'))
   return render_template('index.html')

@app.route('/home')
def home():
   return render_template('home.html')

@app.route('/about')
def about():
   return render_template('about.html')

@app.route('/recommend')
def recommend():
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

        # Filter out track IDs that are not present in the dataset
        matched_track_ids = [
            track_id for track_id in user_top_track_ids if track_id in dataset['track_id_column']
        ]

        # Check if any matched IDs exist
        if not matched_track_ids:
            print("No matching track IDs found in dataset.")
            return jsonify({"error": "No matching tracks found in the dataset."})

        # Proceed with recommendations using matched tracks
        recommendations = hybrid_recommendations(user_top_track_ids, dataset)
        return render_template('recommend.html', recommendations=recommendations)
    else:
        return jsonify({"error": "Failed to get top tracks. Please try again later."})
   


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

      user_profile = requests.get(API_BASE_URL + 'me', headers={'Authorization': f"Bearer {token_info['access_token']}"})
      user_info = user_profile.json()
      session['user_name'] = user_info['display_name']

      return redirect(url_for('home'))
   
'''
@app.route('/playlists')
def get_playlists():
   if 'access_token' not in session:
      return redirect('/login')
   
   # Ensure access token is expired
   if datetime.now().timestamp() > session['expires_at']:
      return redirect('/refresh-token')
   
   headers = {
      'Authorization': f"Bearer {session['access_token']}"
   }

   response = requests.get(API_BASE_URL + 'me/playlists', headers=headers)
   playlists = response.json()

   return render_template('playlists.html', playlists=playlists['items'])

# To check JSON contents only
@app.route('/playlists-json')
def get_playlists_json():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh-token')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    response = requests.get(API_BASE_URL + 'me/playlists', headers=headers)
    playlists = response.json()
    return jsonify(playlists)
'''

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

@app.route('/new_user_recommendations', methods=['POST'])
def new_user_recommendations():
    artist1 = request.form['artist1']
    artist2 = request.form['artist2']
    artist3 = request.form['artist3']

    if 'access_token' not in session:
        return redirect(url_for('login'))
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect(url_for('refresh_token'))

    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    user_top_tracks = get_top_tracks_for_artists([artist1, artist2, artist3])
    user_top_track_ids = [track['id'] for track in user_top_tracks]

    recommendations = hybrid_recommendations(user_top_track_ids, dataset)
    return render_template('new_user.html', recommendations=recommendations)

    '''
    # Search for the artists
    artist_ids = []
    for artist in [artist1, artist2, artist3]:
        response = requests.get(API_BASE_URL + f'search?q={artist}&type=artist', headers=headers)
        result = response.json()
        if result['artists']['items']:
            artist_ids.append(result['artists']['items'][0]['id'])
    
    # Get recommendations based on artist IDs
    artist_ids_str = ','.join(artist_ids)
    response = requests.get(API_BASE_URL + f'recommendations?seed_artists={artist_ids_str}', headers=headers)
    recommendations = response.json()['tracks']

    return render_template('recommendations.html', recommendations=recommendations)
   '''
    
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