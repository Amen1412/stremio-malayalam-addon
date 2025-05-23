from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import time
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

TMDB_API_KEY = "29dfffa9ae088178fa088680b67ce583"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

CACHE_FILE = "data.json"
all_movies_cache = []

def load_cache():
    global all_movies_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                all_movies_cache = json.load(f)
            print(f"[CACHE] Loaded {len(all_movies_cache)} movies from cache ✅")
        except Exception as e:
            print(f"[CACHE ERROR] Failed to load cache: {e}")

def save_cache():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(all_movies_cache, f, ensure_ascii=False, indent=2)
        print(f"[CACHE] Saved {len(all_movies_cache)} movies to cache ✅")
    except Exception as e:
        print(f"[CACHE ERROR] Failed to save cache: {e}")

def fetch_and_cache_movies(max_pages=20, max_duration=20):
    global all_movies_cache
    print("[CACHE] Fetching Malayalam OTT movies...")

    start_time = time.time()
    today = datetime.now().strftime("%Y-%m-%d")
    new_movies = []

    for page in range(1, max_pages + 1):
        if time.time() - start_time > max_duration:
            print(f"[CACHE] Stopping early due to timeout at page {page}")
            break

        print(f"[INFO] Checking page {page}")
        params = {
            "api_key": TMDB_API_KEY,
            "with_original_language": "ml",
            "sort_by": "release_date.desc",
            "release_date.lte": today,
            "region": "IN",
            "page": page
        }

        try:
            response = requests.get(f"{TMDB_BASE_URL}/discover/movie", params=params, timeout=10)
            results = response.json().get("results", [])
            if not results:
                break

            for movie in results:
                movie_id = movie.get("id")
                title = movie.get("title")
                if not movie_id or not title:
                    continue

                providers_url = f"{TMDB_BASE_URL}/movie/{movie_id}/watch/providers"
                prov_response = requests.get(providers_url, params={"api_key": TMDB_API_KEY}, timeout=5)
                prov_data = prov_response.json()

                if "results" in prov_data and "IN" in prov_data["results"]:
                    if "flatrate" in prov_data["results"]["IN"]:
                        ext_url = f"{TMDB_BASE_URL}/movie/{movie_id}/external_ids"
                        ext_response = requests.get(ext_url, params={"api_key": TMDB_API_KEY}, timeout=5)
                        ext_data = ext_response.json()
                        imdb_id = ext_data.get("imdb_id")

                        if imdb_id and imdb_id.startswith("tt"):
                            movie["imdb_id"] = imdb_id
                            new_movies.append(movie)

        except Exception as e:
            print(f"[ERROR] Page {page} failed: {e}")
            break

    # Deduplicate against existing cache
    seen_ids = set(movie.get("imdb_id") for movie in all_movies_cache if movie.get("imdb_id"))
    added = 0
    for movie in new_movies:
        imdb_id = movie.get("imdb_id")
        if imdb_id and imdb_id not in seen_ids:
            seen_ids.add(imdb_id)
            all_movies_cache.append(movie)
            added += 1

    save_cache()
    print(f"[CACHE] Added {added} new movies ✅ — total now: {len(all_movies_cache)}")

def to_stremio_meta(movie):
    try:
        imdb_id = movie.get("imdb_id")
        title = movie.get("title")
        if not imdb_id or not title:
            return None

        return {
            "id": imdb_id,
            "type": "movie",
            "name": title,
            "poster": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else None,
            "description": movie.get("overview", ""),
            "releaseInfo": movie.get("release_date", ""),
            "background": f"https://image.tmdb.org/t/p/w780{movie['backdrop_path']}" if movie.get("backdrop_path") else None
        }
    except Exception as e:
        print(f"[ERROR] to_stremio_meta failed: {e}")
        return None

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
        metas = [meta for meta in (to_stremio_meta(m) for m in all_movies_cache) if meta]
        print(f"[INFO] Returning {len(metas)} total movies ✅")
        return jsonify({"metas": metas})
    except Exception as e:
        print(f"[ERROR] Catalog error: {e}")
        return jsonify({"metas": []})

@app.route("/refresh")
def refresh():
    try:
        fetch_and_cache_movies(max_pages=20, max_duration=20)
        return jsonify({"status": "refreshed", "count": len(all_movies_cache)})
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(f"[REFRESH ERROR] {traceback_str}")
        return jsonify({"error": str(e), "trace": traceback_str}), 500

# Load cache on startup
load_cache()

# If no cache is loaded, do a full fetch (once only, useful on first deploy)
if len(all_movies_cache) == 0:
    print("[CACHE] No existing cache found — doing one-time initial fetch")
    fetch_and_cache_movies(max_pages=100, max_duration=30)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)
