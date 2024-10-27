from flask import Flask, render_template, session

app = Flask(__name__)
# app.secret_key = '7Yb29#pLw*QfMv!Xt8J3zDk@5eH1Ua%'

# CLIENT_ID = 'c4ccf9590da446f591e8d6520db66971'
# CLIENT_SECRET = '945eadb35b8a494b9740c1a64cf55c19'
# REDIRECT_URI = 'http://localhost:5000/callback'

# AUTH_URL = 'https://accounts.spotify.com/authorize'
# TOKEN_URL = 'https://accounts.spotify.com/api/token'
# API_BASE_URL = 'https://api.spotify.com/v1/'

@app.route("/")
def index():
   return render_template('index.html')

@app.route('/home')
def home():
   return render_template('home.html')

# Run Flask server
if __name__ == '__main__':
   app.run(host='0.0.0.0', debug=True)