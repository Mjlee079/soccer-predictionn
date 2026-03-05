"""
Football API Client  (Free-tier compatible)
============================================
Fetches real match data from v3.football.api-sports.io.
Uses season-based endpoints (the only ones that work on the free plan).
Caches results locally to avoid burning API calls.

Set your key:  $env:FOOTBALL_API_KEY = 'your_key'
"""
import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

BASE_URL = "https://v3.football.api-sports.io"
CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")


def _get_api_key():
    key = os.environ.get("FOOTBALL_API_KEY")
    if not key:
        raise RuntimeError(
            "FOOTBALL_API_KEY not set.\n"
            "Run:  $env:FOOTBALL_API_KEY = 'your_key'"
        )
    return key


# ── Cache ────────────────────────────────────────────────────
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_key(endpoint, params):
    safe = endpoint.replace("/", "_") + "_" + urllib.parse.urlencode(sorted(params.items()))
    return os.path.join(CACHE_DIR, safe + ".json")


def _read_cache(path, max_age=3600):
    """Return cached JSON if fresh enough, else None."""
    if not os.path.exists(path):
        return None
    age = time.time() - os.path.getmtime(path)
    if age > max_age:
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_cache(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ── HTTP ─────────────────────────────────────────────────────
def _request(endpoint, params=None):
    if params is None:
        params = {}
    cache_path = _cache_key(endpoint, params)
    cached = _read_cache(cache_path)
    if cached is not None:
        return cached

    url = f"{BASE_URL}/{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url)
    req.add_header("x-apisports-key", _get_api_key())

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            _write_cache(cache_path, data)
            return data
    except urllib.error.HTTPError as e:
        print(f"  [API Error] {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        print(f"  [Network Error] {e.reason}")
    return None


# ── Season helper ────────────────────────────────────────────
def _current_season():
    now = datetime.now()
    return now.year if now.month >= 7 else now.year - 1


def _best_season():
    """Return current season; if no data exists, try previous."""
    return _current_season()  # fallback handled per-team below


# ── Teams ────────────────────────────────────────────────────
def search_teams(name):
    data = _request("teams", {"search": name})
    if not data or not data.get("response"):
        return []
    return [
        {"id": t["team"]["id"],
         "name": t["team"]["name"],
         "country": t["team"].get("country", "")}
        for t in data["response"]
    ]


# ── Fixtures (season-based) ─────────────────────────────────
def _parse_fixtures(raw_list):
    results = []
    for fx in raw_list:
        info = fx.get("fixture", {})
        teams = fx.get("teams", {})
        goals = fx.get("goals", {})
        results.append({
            "id": info.get("id"),
            "date": info.get("date", "")[:10],
            "status": info.get("status", {}).get("short", ""),
            "home": teams.get("home", {}).get("name", ""),
            "home_id": teams.get("home", {}).get("id"),
            "away": teams.get("away", {}).get("name", ""),
            "away_id": teams.get("away", {}).get("id"),
            "home_goals": goals.get("home"),
            "away_goals": goals.get("away"),
            "league": fx.get("league", {}).get("name", ""),
        })
    return results


def get_team_season(team_id, season=None):
    """Get all fixtures for a team in a season. Tries current, then previous."""
    if season is None:
        season = _current_season()
    data = _request("fixtures", {"team": team_id, "season": season})
    if data and data.get("response"):
        return _parse_fixtures(data["response"])
    # fallback
    data = _request("fixtures", {"team": team_id, "season": season - 1})
    if data and data.get("response"):
        return _parse_fixtures(data["response"])
    return []


def get_finished_matches(team_id, season=None):
    """Get completed matches only."""
    all_fx = get_team_season(team_id, season)
    return [m for m in all_fx if m["status"] in ("FT", "AET", "PEN")]


def get_last_n(team_id, n=10, season=None):
    """Most recent N completed matches."""
    finished = get_finished_matches(team_id, season)
    finished.sort(key=lambda m: m["date"], reverse=True)
    return finished[:n]


def get_upcoming(team_id, n=5, season=None):
    """Next N scheduled matches."""
    all_fx = get_team_season(team_id, season)
    upcoming = [m for m in all_fx if m["status"] in ("NS", "TBD", "")]
    upcoming.sort(key=lambda m: m["date"])
    return upcoming[:n]


def get_h2h(team_a_id, team_b_id, season=None):
    """Head-to-head from season data (free-tier compatible)."""
    a_matches = get_team_season(team_a_id, season)
    b_ids = {m["id"] for m in get_team_season(team_b_id, season)}
    h2h = [m for m in a_matches if m["id"] in b_ids and m["status"] in ("FT", "AET", "PEN")]
    h2h.sort(key=lambda m: m["date"], reverse=True)
    return h2h
