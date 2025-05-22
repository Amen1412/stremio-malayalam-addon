from flask import Flask, jsonify
from flask_cors import CORS
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

TMDB_API_KEY = "29dfffa9ae088178fa088680b67ce583"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# In-memory cache for both languages
movie_cache = {
    "malayalam": [],
    "hindi": []
}

# Function to fetch and cache movies
def fetch_movies(language_code):
    print(f"[FETCH] Getting {language_code.upper()} OTT movies")
    today = datetime.now().strftime("%Y-%m-%d")
    final_movies = []

    for page in range(1, 1000):
        print(f"[{language_code}] Checking page {page}")
        params = {
            "api_key": TMDB_API_KEY,
            "with_original_language": language_code,
            "sort_by": "release_date.desc",
            "release_date.lte": today,
            "region": "IN",
            "page": page
        }

        try:
            response = requests.get(f"{TMDB_BASE_URL}/discover/movie", params=params)
            results = response.json().get("results", [])
            if not results:
                break

            for movie in results:
                movie_id = movie.get("id")
                title = movie.get("title")
                if not movie_id or not title:
                    continue

                # Check OTT availability
                providers_url = f"{TMDB_BASE_URL}/movie/{movie_id}/watch/providers"
                prov_response = requests.get(providers_url, params={"api_key": TMDB_API_KEY})
                prov_data = prov_response.json()

                if "results" in prov_data and "IN" in prov_data["results"]:
                    if "flatrate" in prov_data["results"]["IN"]:
                        # Get IMDb ID
                        ext_url = f"{TMDB_BASE_URL}/movie/{movie_id}/external_ids"
                        ext_response = requests.get(ext_url, params={"api_key": TMDB_API_KEY})
                        ext_data = ext_response.json()
                        imdb_id = ext_data.get("imdb_id")

                        if imdb_id and imdb_id.startswith("tt"):
                            movie["imdb_id"] = imdb_id
                            final_movies.append(movie)

        except Exception as e:
            print(f"[{language_code}] Error on page {page}: {e}")
            break

    # Remove duplicates
    seen = set()
    unique = []
    for m in final_movies:
        if m["imdb_id"] not in seen:
            seen.add(m["imdb_id"])
            unique.append(m)

    movie_cache[language_code] = unique
    print(f"[CACHE] {language_code.upper()} total: {len(unique)} ✅")

# Convert TMDB movie to Stremio meta format
def to_stremio_meta(movie):
    try:
        return {
            "id": movie.get("imdb_id"),
            "type": "movie",
            "name": movie.get("title"),
            "poster": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else None,
            "description": movie.get("overview", ""),
            "releaseInfo": movie.get("release_date", ""),
            "background": f"https://image.tmdb.org/t/p/w780{movie['backdrop_path']}" if movie.get("backdrop_path") else None
        }
    except:
        return None

# Manifest with two catalogs
@app.route("/manifest.json")
def manifest():
    return jsonify({
        "id": "org.dual.catalog",
        "version": "1.0.0",
        "name": "Malayalam + Hindi",
        "description": "Latest Malayalam and Hindi Movies on OTT",
        "resources": ["catalog"],
        "types": ["movie"],
        "catalogs": [
            {
                "type": "movie",
                "id": "malayalam",
                "name": "Malayalam"
            },
            {
                "type": "movie",
                "id": "hindi",
                "name": "Hindi"
            }
        ],
        "idPrefixes": ["tt"]
    })

# Catalog route
@app.route("/catalog/movie/<catalog_id>.json")
def catalog(catalog_id):
    if catalog_id not in movie_cache:
        return jsonify({"metas": []})

    print(f"[SERVE] Sending catalog: {catalog_id}")
    metas = [m for m in (to_stremio_meta(movie) for movie in movie_cache[catalog_id]) if m]
    return jsonify({"metas": metas})

# Manual refresh
@app.route("/refresh")
def refresh():
    try:
        fetch_movies("ml")   # Malayalam
        fetch_movies("hi")   # Hindi
        return jsonify({
            "status": "refreshed",
            "malayalam": len(movie_cache["malayalam"]),
            "hindi": len(movie_cache["hindi"])
        })
    except Exception as e:
        return jsonify({"error": str(e)})

# Fetch both on startup
fetch_movies("ml")
fetch_movies("hi")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)
