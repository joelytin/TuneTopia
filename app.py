from flask import Flask, render_template, redirect, url_for, session, request, jsonify
from model import recommend_songs, evaluate_model, df
import pandas as pd
import re

app = Flask(__name__)
app.jinja_env.globals.update(zip=zip)
app.secret_key = '7Yb29#pLw*QfMv!Xt8J3zDk@5eH1Ua%'

# Load and preprocess the dataset
dataset = pd.read_csv('data/huggingface.csv', low_memory=False)

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
   if artist_popularity[artist]['count'] > 0:
      artist_popularity[artist] = artist_popularity[artist]['popularity'] / artist_popularity[artist]['count']
   else:
      artist_popularity[artist] = 0  # Set default value to avoid division error

# Extract unique artist names
unique_artists = set(artist_popularity.keys())

@app.route('/')
def index():
   return render_template('home.html')

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

      try:
         alpha = float(request.form.get('alpha', 0.5))  # Default to 0.5 if not provided
         num_songs = int(request.form.get('num_songs', 15))  # Default to 15
      except ValueError:
         return render_template("recommend.html", error="Invalid input for alpha or number of songs.")
      
      if alpha is None or not (0.0 <= alpha <= 1.0) or num_songs not in [5, 10, 15, 20]:
        return render_template("recommend.html", error="Invalid input for alpha or number of songs.")

      if not artist_name:
         return render_template("recommend.html", error="Please enter an artist name.")
   
      if alpha < 0 or alpha > 1:
        return render_template("recommend.html", error="Alpha must be between 0 and 1.")
   
      if num_songs <= 0 or num_songs > 20:
        return render_template("recommend.html", error="Please select between 1 and 20 songs.")

      recommended_songs = recommend_songs(artist_name, df, num_songs=num_songs, alpha=alpha)

      if recommended_songs is None:
         return render_template("recommend.html", error="Artist not found in the dataset.")
      
      # Check if artist exists in dataset
      artist_tracks = df[df['artists'].str.contains(artist_name, case=False, na=False)]

      if artist_tracks.empty:
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
   query = request.args.get('query', '').strip().lower()
   if not query:
      return jsonify({"error": "Query parameter is required."}), 400

   # Normalise spaces in query (replace multiple spaces with a single space)
   normalized_query = re.sub(r'\s+', ' ', query)

   # Filter artists whose names start with or contain the query (case-insensitive)
   starts_with_matches = [artist for artist in unique_artists if artist.lower().startswith(normalized_query)]
   contains_matches = [artist for artist in unique_artists if normalized_query in artist.lower() and artist not in starts_with_matches]

   # Combine and retrieve popularity
   matched_artists = starts_with_matches + contains_matches
   matched_artists_info = [{'name': artist.title()} for artist in matched_artists]  # Capitalize names

   return jsonify(matched_artists_info[:10])  # Limit to top 10 results for efficiency

if __name__ == '__main__':
   app.run(debug=True)
