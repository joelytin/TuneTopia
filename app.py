from flask import Flask, render_template, redirect, url_for, session, request, jsonify
from model import recommend_songs, evaluate_model, df
import pandas as pd
import re

app = Flask(__name__)
app.jinja_env.globals.update(zip=zip)
app.secret_key = '7Yb29#pLw*QfMv!Xt8J3zDk@5eH1Ua%'

# Load and preprocess the dataset
dataset = pd.read_csv('data/huggingface.csv')

artist_popularity = {}  # Initialize dictionaries to store artist popularity and unique artists

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

@app.route('/')
def index():
   return render_template('home.html')

@app.route('/test')
def test():
   return render_template('test.html')

@app.route('/home')
def home():
   return render_template('home.html')

@app.route('/about')
def about():
   return render_template('about.html')

@app.route('/recommend', methods=['GET', 'POST'])
def recommend():
   if request.method == 'GET':
      return render_template('recommend.html')

   elif request.method == 'POST':
      artist_name = request.form.get('artist', '').strip()
      alpha = float(request.form.get('alpha', 0.5))  # Default to 0.5 if not provided
      num_songs = int(request.form.get('num_songs', 15))  # Default to 15

      if not artist_name:
         return render_template("recommend.html", error="Please enter an artist name.")

      recommended_songs = recommend_songs(artist_name, df, num_songs=num_songs, alpha=alpha)

      if recommended_songs is None:
         return render_template("recommend.html", error="Artist not found in the dataset.")

      input_genre = df[df['artists'].str.contains(artist_name, case=False, na=False)].iloc[0]['track_genre']
      evaluation_results = evaluate_model(recommended_songs, input_genre, num_songs)

      return render_template("result.html",
                              artist_name=artist_name,
                              recommendations=recommended_songs.to_dict(orient='records'),
                              evaluation_results=evaluation_results)


@app.route('/metronome')
def metronome():
   return render_template('metronome.html')

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

   # Limit results to top 20 for efficiency
   return jsonify(sorted_artists[:20])

if __name__ == '__main__':
   app.run(debug=True)
