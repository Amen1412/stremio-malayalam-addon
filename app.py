from flask import Flask, jsonify
from flask_cors import CORS
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)  # This fixes the "Failed to fetch" issue in Stremio

TMDB_API_KEY = "29dfffa9ae088178fa088680b67ce583"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

def get_malayalam_movies(limit=10):
    print("[INFO] Fetching Malayalam movies from TMDB")

    today = datetime.now().strftime("%Y-%m-%d")
    url = f"{TMDB_BASE_URL}/discover/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "with_original_language": "ml",
        "sort_by": "release_date.desc",
        "release_date.lte": today,
        "with_watch_monetization_types": "flatrate",  # streaming only
        "region": "IN",  # optional, for better results in India
        "page": 1
    }

    response = requests.get(url, params=params)
    data = response.json()
    movies = data.get("results", [])[:limit]

    print(f"[INFO] Found {len(movies)} Malayalam OTT movies")
    return movies

def to_stremio_meta(movie):
    return {
        "id": str(movie["id"]),
        "type": "movie",
        "name": movie.get("title"),
        "poster": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else None,
        "description": movie.get("overview"),
        "releaseInfo": movie.get("release_date", ""),
        "background": f"https://image.tmdb.org/t/p/w780{movie['backdrop_path']}" if movie.get("backdrop_path") else None
    }

@app.route("/manifest.json")
def manifest():
    return jsonify({
        "id": "org.malayalam.catalog",
        "version": "1.0.0",
        "name": "Malayalam",
        "description": "Latest Malayalam Movies on OTT",
        "resources": ["catalog"],
        "types": ["movie"],
        "catalogs": [{
            "type": "movie",
            "id": "malayalam",
            "name": "Malayalam"
        }],
        "idPrefixes": ["tt"]
    })

@app.route("/catalog/movie/malayalam.json")
def catalog():
    print("[INFO] Catalog requested")

    try:
        movies = get_malayalam_movies(limit=10)
        metas = [to_stremio_meta(m) for m in movies]
        print(f"[INFO] Returning {len(metas)} metas")
        return jsonify({"metas": metas})
    except Exception as e:
        print(f"[ERROR] Failed to build catalog: {e}")
        return jsonify({"metas": []})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)
