from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

TMDB_API_KEY = "29dfffa9ae088178fa088680b67ce583"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Global movie cache
all_movies_cache = []

def fetch_and_cache_movies():
    global all_movies_cache
    print("[CACHE] Building Malayalam OTT movie list...")

    today = datetime.now().strftime("%Y-%m-%d")
    final_movies = []

    for page in range(1, 1000):
        print(f"[INFO] Page {page}")
        params = {
            "api_key": TMDB_API_KEY,
            "with_original_language": "ml",
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
                if not movie_id:
                    continue

                prov_resp = requests.get(
                    f"{TMDB_BASE_URL}/movie/{movie_id}/watch/providers",
                    params={"api_key": TMDB_API_KEY}
                )
                prov_data = prov_resp.json()
                if "results" in prov_data and "IN" in prov_data["results"]:
                    if "flatrate" in prov_data["results"]["IN"]:
                        final_movies.append(movie)

        except Exception as e:
            print(f"[ERROR] Page {page} failed: {e}")
            break

    all_movies_cache = final_movies
    print(f"[CACHE] Fetched {len(final_movies)} Malayalam OTT movies ✅")


def to_stremio_meta(movie):
    if not movie.get("id") or not movie.get("title"):
        return None  # skip invalid or incomplete entries

    return {
        "id": str(movie["id"]),
        "type": "movie",
        "name": movie["title"],
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
        skip = int(request.args.get("skip", 0))
        page_size = 100

        if not all_movies_cache:
            print("[WARN] Cache is empty")
            return jsonify({"metas": []})

        sliced = all_movies_cache[skip:skip + page_size]
        metas = [meta for meta in (to_stremio_meta(m) for m in sliced) if meta]
        print(f"[INFO] Returning {len(metas)} metas (skip={skip})")
        return jsonify({"metas": metas})

    except Exception as e:
        print(f"[ERROR] Catalog error: {e}")
        return jsonify({"metas": []})


# ✅ Immediately load movie cache on start
fetch_and_cache_movies()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)
