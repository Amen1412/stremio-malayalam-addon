from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import threading
import time

app = Flask(__name__)
CORS(app)

PORT = 10000  # required for Render port binding

TMDB_API_KEY = "YOUR_TMDB_API_KEY"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
LANGUAGES = {
    "malayalam": "ml",
    "hindi": "hi"
}

movies_cache = {
    "malayalam": [],
    "hindi": []
}

def fetch_movies(language_code, category):
    url = f"{TMDB_BASE_URL}/discover/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "with_original_language": language_code,
        "sort_by": "popularity.desc",
        "page": 1
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json().get("results", [])

def build_meta(movie):
    return {
        "id": str(movie["id"]),
        "type": "movie",
        "name": movie.get("title"),
        "poster": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else "",
        "description": movie.get("overview", "")
    }

def update_cache():
    while True:
        for key, lang_code in LANGUAGES.items():
            try:
                print(f"Fetching {key} movies...")
                raw = fetch_movies(lang_code, "movie")
                movies_cache[key] = [build_meta(movie) for movie in raw]
            except Exception as e:
                print(f"Failed to update {key} movies: {e}")
        time.sleep(86400)  # Refresh every 24 hours

# Start cache update thread
threading.Thread(target=update_cache, daemon=True).start()

@app.route("/manifest.json")
def manifest():
    return jsonify({
        "id": "org.stremio.malayalam.hindi",
        "version": "1.0.0",
        "name": "Indian Movies Addon",
        "description": "Shows Malayalam and Hindi movies from TMDB",
        "resources": ["catalog", "meta"],
        "types": ["movie"],
        "catalogs": [
            {
                "type": "movie",
                "id": "malayalam",
                "name": "Malayalam Movies"
            },
            {
                "type": "movie",
                "id": "hindi",
                "name": "Hindi Movies"
            }
        ]
    })

@app.route("/catalog/<type>/<id>.json")
def catalog(type, id):
    if id in movies_cache:
        return jsonify({"metas": movies_cache[id]})
    return jsonify({"metas": []})

@app.route("/meta/<type>/<id>.json")
def meta(type, id):
    for lang_movies in movies_cache.values():
        for movie in lang_movies:
            if movie["id"] == id:
                return jsonify({"meta": movie})
    return jsonify({})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
