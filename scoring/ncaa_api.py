"""NCAA API client — fetch scoreboard and box scores.

API docs: https://github.com/henrygd/ncaa-api
Base URL: https://ncaa-api.henrygd.me
Rate limit: 5 req/s (we use 200ms sleep between requests)
"""

import json
import time
import urllib.request
from typing import Optional

from scoring.models import API_BASE_URL, API_ROUND_MAP, ROUND_DATES


def _fetch_json(path: str, retries: int = 2) -> Optional[dict]:
    """GET a JSON endpoint from the NCAA API. Returns None on error.

    Retries on 403/502 with exponential backoff.
    """
    url = f"{API_BASE_URL}{path}"
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "MarchMadnessTracker/1.0"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            if attempt < retries:
                wait = 1.0 * (attempt + 1)
                print(f"  [RETRY] {url}: {exc} (waiting {wait}s)")
                time.sleep(wait)
            else:
                print(f"  [WARN] API error for {url}: {exc}")
                return None
        finally:
            time.sleep(0.3)  # rate limit: stay well under 5 req/s
    return None


def fetch_scoreboard(date: str) -> list[dict]:
    """Fetch all tournament games for a given date (YYYY-MM-DD).

    Returns list of game dicts with keys:
        game_id, round, date, status, away, home, bracket_round
    """
    year, month, day = date.split("-")
    path = f"/scoreboard/basketball-men/d1/{year}/{month}/{day}/all-conf"
    data = _fetch_json(path)
    if not data:
        return []

    games = []
    for entry in data.get("games", []):
        game = entry.get("game", {})
        bracket_round = game.get("bracketRound")

        # Skip non-tournament games (bracketRound 1 = First Four, 2+ = main bracket)
        if not bracket_round or bracket_round < 1:
            continue

        round_name = API_ROUND_MAP.get(bracket_round, f"R{bracket_round}")

        away = game.get("away", {})
        home = game.get("home", {})

        games.append({
            "game_id": str(game.get("gameID", "")),
            "round": round_name,
            "date": date,
            "status": game.get("gameState", "unknown"),
            "away": {
                "name": away.get("names", {}).get("short", ""),
                "seed": _parse_int(away.get("seed", "")),
                "score": _parse_int(away.get("score", "0")),
                "winner": away.get("winner", False),
            },
            "home": {
                "name": home.get("names", {}).get("short", ""),
                "seed": _parse_int(home.get("seed", "")),
                "score": _parse_int(home.get("score", "0")),
                "winner": home.get("winner", False),
            },
        })

    return games


def fetch_boxscore(game_id: str) -> dict:
    """Fetch box score for a single game.

    Returns dict with keys:
        game_id, teams (list of {team_id, name, players})
        Each player has: first_name, last_name, points, minutes, ...
    """
    data = _fetch_json(f"/game/{game_id}/boxscore")
    if not data:
        return {"game_id": game_id, "teams": []}

    # Build team_id → team_name lookup
    team_lookup: dict[str, str] = {}
    for team in data.get("teams", []):
        tid = str(team.get("teamId", ""))
        team_lookup[tid] = team.get("nameShort", "")

    teams = []
    for team_box in data.get("teamBoxscore", []):
        tid = str(team_box.get("teamId", ""))
        team_name = team_lookup.get(tid, "")

        players = []
        for p in team_box.get("playerStats", []):
            players.append({
                "first_name": p.get("firstName", ""),
                "last_name": p.get("lastName", ""),
                "points": _parse_int(p.get("points", "0")),
                "minutes": p.get("minutesPlayed", "0"),
                "fg": f"{p.get('fieldGoalsMade', '0')}/{p.get('fieldGoalsAttempted', '0')}",
                "three": f"{p.get('threePointsMade', '0')}/{p.get('threePointsAttempted', '0')}",
                "ft": f"{p.get('freeThrowsMade', '0')}/{p.get('freeThrowsAttempted', '0')}",
                "rebounds": _parse_int(p.get("totalRebounds", "0")),
                "assists": _parse_int(p.get("assists", "0")),
                "steals": _parse_int(p.get("steals", "0")),
                "blocks": _parse_int(p.get("blockedShots", "0")),
                "turnovers": _parse_int(p.get("turnovers", "0")),
            })

        teams.append({
            "team_id": tid,
            "name": team_name,
            "players": players,
        })

    return {"game_id": game_id, "teams": teams}


def fetch_round_games(round_name: str) -> list[dict]:
    """Fetch all games for a tournament round, with box scores embedded.

    Returns list of game dicts, each enriched with player_stats from box scores.
    """
    dates = ROUND_DATES.get(round_name, [])
    if not dates:
        print(f"  [WARN] No dates configured for round {round_name}")
        return []

    all_games = []
    for date in dates:
        print(f"  Fetching scoreboard for {date}...")
        games = fetch_scoreboard(date)
        round_games = [g for g in games if g["round"] == round_name]
        print(f"    Found {len(round_games)} {round_name} games")

        for game in round_games:
            # Skip games that haven't started — no box score available
            if game["status"] == "pre":
                continue

            status_tag = "LIVE" if game["status"] != "final" else "FINAL"
            print(f"    [{status_tag}] {game['away']['name']} vs {game['home']['name']}...")
            boxscore = fetch_boxscore(game["game_id"])
            game["player_stats"] = []

            for team in boxscore.get("teams", []):
                for player in team.get("players", []):
                    game["player_stats"].append({
                        **player,
                        "team": team["name"],
                    })

            all_games.append(game)

    return all_games


def _parse_int(value: str) -> int:
    """Safely parse a string to int, defaulting to 0."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0
