from flask import Flask, jsonify
from flask_cors import CORS
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

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
        "region": "IN",
        "page": 1
    }

    response = requests.get(url, params=params)
    data = response.json()
    candidates = data.get("results", [])

    final_movies = []

    for movie in candidates:
        movie_id = movie.get("id")
        if not movie_id:
            continue

        providers_url = f"{TMDB_BASE_URL}/movie/{movie_id}/watch/providers"
        prov_response = requests.get(providers_url, params={"api_key": TMDB_API_KEY})
        prov_data = prov_response.json()

        # Check if at least one OTT provider is available in India
        if "results" in prov_data and "IN" in prov_data["results"]:
            country_info = prov_data["results"]["IN"]
            if "flatrate" in country_info:
                final_movies.append(movie)

        if len(final_movies) >= limit:
            break

    print(f"[INFO] Returning {len(final_movies)} Malayalam OTT movies")
    return final_movies

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
