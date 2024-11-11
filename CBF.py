import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pandas as pd

# Initialize Spotify API client
CLIENT_ID = 'c4ccf9590da446f591e8d6520db66971'
CLIENT_SECRET = '945eadb35b8a494b9740c1a64cf55c19'
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))

# Step 1: Function to get audio features for an artist's songs
def get_artist_audio_features(artist_name):
    results = sp.search(q='artist:' + artist_name, type='track', limit=50)
    track_ids = [track['id'] for track in results['tracks']['items']]
    audio_features = sp.audio_features(track_ids)
    return pd.DataFrame(audio_features)

# Example artists entered by the user
artist_names = ['CHUU', 'RESCENE', 'LOONA']
all_artist_features = pd.concat([get_artist_audio_features(name) for name in artist_names], ignore_index=True)

# Step 2: Calculate the average audio features to form a user preference profile
features = ['danceability', 'energy', 'loudness', 'speechiness', 'acousticness',
            'instrumentalness', 'liveness', 'valence', 'tempo']
user_profile = all_artist_features[features].mean().to_dict()

# Step 3: Use Spotify's recommendation endpoint to find similar songs
recommendations = sp.recommendations(seed_tracks=None,
                                     limit=10,
                                     target_danceability=user_profile['danceability'],
                                     target_energy=user_profile['energy'],
                                     target_loudness=user_profile['loudness'],
                                     target_speechiness=user_profile['speechiness'],
                                     target_acousticness=user_profile['acousticness'],
                                     target_instrumentalness=user_profile['instrumentalness'],
                                     target_liveness=user_profile['liveness'],
                                     target_valence=user_profile['valence'],
                                     target_tempo=user_profile['tempo'])

# Display recommendations
recommended_tracks = [(track['name'], track['artists'][0]['name']) for track in recommendations['tracks']]
print("Recommended Songs:")
for track in recommended_tracks:
    print(f"Song: {track[0]}, Artist: {track[1]}")