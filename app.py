from flask import Flask, jsonify, request
import requests
from datetime import datetime

app = Flask(__name__)

TMDB_API_KEY = "29dfffa9ae088178fa088680b67ce583"
TMDB_BASE_URL = "https://api.themoviedb.org/3"


def fetch_movies(language_code):
    today = datetime.now().strftime("%Y-%m-%d")
    all_movies = []
    for page in range(1, 10):  # Adjust number of pages as needed
        url = f"{TMDB_BASE_URL}/discover/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "with_original_language": language_code,
            "sort_by": "release_date.desc",
            "release_date.lte": today,
            "with_watch_monetization_types": "flatrate",
            "region": "IN",
            "page": page
        }
        res = requests.get(url, params=params)
        if res.status_code != 200:
            break
        data = res.json()
        results = data.get("results", [])
        if not results:
            break
        all_movies.extend(results)
    return all_movies


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
        "id": "org.malayalam.hindi.catalog",
        "version": "1.0.0",
        "name": "Malayalam + Hindi OTT",
        "description": "Latest Malayalam & Hindi Movies on OTT",
        "resources": ["catalog"],
        "types": ["movie"],
        "catalogs": [
            {"type": "movie", "id": "malayalam", "name": "Malayalam"},
            {"type": "movie", "id": "hindi", "name": "Hindi"}
        ],
        "idPrefixes": ["tt"]
    })


@app.route("/catalog/movie/<catalog_id>.json")
def catalog(catalog_id):
    try:
        if catalog_id == "malayalam":
            movies = fetch_movies("ml")
        elif catalog_id == "hindi":
            movies = fetch_movies("hi")
        else:
            return jsonify({"metas": []})
        metas = [to_stremio_meta(m) for m in movies]
        return jsonify({"metas": metas})
    except Exception as e:
        print(f"[ERROR] Catalog fetch failed: {e}")
        return jsonify({"metas": []})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
