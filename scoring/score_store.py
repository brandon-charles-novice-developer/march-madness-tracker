"""Score persistence, player name matching, and elimination detection."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scoring.models import NAME_SUFFIXES, ROUND_ORDER

DATA_DIR = Path(__file__).parent.parent / "data"
SCORES_FILE = DATA_DIR / "tournament_scores.json"
GAMES_FILE = DATA_DIR / "tournament_games.json"


def load_scores() -> dict:
    """Load tournament_scores.json or return empty structure."""
    if SCORES_FILE.exists():
        with open(SCORES_FILE) as f:
            return json.load(f)
    return _empty_scores()


def save_scores(scores: dict) -> None:
    """Write scores to disk with updated timestamp."""
    updated = {
        **scores,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    with open(SCORES_FILE, "w") as f:
        json.dump(updated, f, indent=2)
    print(f"  Saved scores to {SCORES_FILE.name}")


def load_players_db() -> list[dict]:
    """Load the player database from players.json."""
    with open(DATA_DIR / "players.json") as f:
        return json.load(f)["players"]


def load_draft_picks() -> list[dict]:
    """Load draft picks from draft_state.json."""
    with open(DATA_DIR / "draft_state.json") as f:
        return json.load(f)["picks"]


def load_games() -> list[dict]:
    """Load persisted game results from tournament_games.json."""
    if GAMES_FILE.exists():
        with open(GAMES_FILE) as f:
            return json.load(f)
    return []


def save_games(games: list[dict]) -> None:
    """Persist game results to tournament_games.json."""
    with open(GAMES_FILE, "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2)
    print(f"  Saved {len(games)} games to {GAMES_FILE.name}")


def merge_round_scores(
    scores: dict,
    round_name: str,
    api_games: list[dict],
    players_db: list[dict],
    draft_picks: list[dict],
) -> dict:
    """Merge API game data into scores. Returns new dict (immutable).

    Matches API player names to drafted players, accumulates points,
    and detects team eliminations from game results.
    """
    # Build set of drafted player names for quick lookup
    drafted_names = {pick["player"] for pick in draft_picks}

    new_player_scores = dict(scores.get("scores", {}))
    new_games = list(scores.get("games_processed", []))
    new_eliminated = list(scores.get("eliminated_teams", []))

    for game in api_games:
        game_id = game["game_id"]
        if game_id in new_games:
            continue  # already processed (idempotent)

        if game["status"] != "final":
            continue  # skip in-progress games

        # Process player stats
        for player_stat in game.get("player_stats", []):
            first = player_stat.get("first_name", "")
            last = player_stat.get("last_name", "")
            api_team = player_stat.get("team", "")
            points = player_stat.get("points", 0)

            matched_name = match_player(
                first, last, api_team, players_db, drafted_names
            )
            if not matched_name:
                continue

            # Update player's round score
            existing = new_player_scores.get(matched_name, {})
            existing_round = existing.get(round_name, 0)
            new_player_scores[matched_name] = {
                **existing,
                round_name: existing_round + points,
            }

        # Detect eliminations
        eliminated_team = _get_eliminated_team(game)
        if eliminated_team and eliminated_team not in new_eliminated:
            new_eliminated.append(eliminated_team)
            print(f"    Eliminated: {eliminated_team}")

        new_games.append(game_id)

    return {
        **scores,
        "scores": new_player_scores,
        "games_processed": new_games,
        "eliminated_teams": sorted(new_eliminated),
    }


def match_player(
    api_first: str,
    api_last: str,
    api_team: str,
    players_db: list[dict],
    drafted_names: set[str],
) -> Optional[str]:
    """Match an API player name to a drafted player name.

    Returns the canonical name from players.json, or None if not drafted.
    """
    api_full = _normalize_name(f"{api_first} {api_last}")
    api_last_norm = _normalize_name(api_last)

    # Pass 1: exact full name match against drafted players
    for name in drafted_names:
        if _normalize_name(name) == api_full:
            return name

    # Pass 2: match against players_db (which has more players than drafted)
    # then check if that player was drafted
    for player in players_db:
        db_name = player["name"]
        db_team = player["team"]

        # Full name match
        if _normalize_name(db_name) == api_full:
            if db_name in drafted_names:
                return db_name
            return None  # in DB but not drafted

        # Last name + same team (handles first name variations)
        db_parts = db_name.split()
        db_last = _normalize_name(db_parts[-1]) if db_parts else ""
        if db_last == api_last_norm and _teams_match(api_team, db_team):
            if db_name in drafted_names:
                return db_name
            return None

    return None


def _normalize_name(name: str) -> str:
    """Normalize a player name for matching: lowercase, strip suffixes."""
    normalized = name.lower().strip()
    # Remove suffixes
    for suffix in NAME_SUFFIXES:
        pattern = rf"\s+{re.escape(suffix)}$"
        normalized = re.sub(pattern, "", normalized)
    # Remove extra whitespace
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _teams_match(api_team: str, db_team: str) -> bool:
    """Check if API team name matches our database team name.

    Handles abbreviation differences like 'Texas Tech' vs 'Texas Tech',
    'Ohio St.' vs 'Ohio St', 'St. Mary's' vs 'Saint Mary's'.
    """
    a = api_team.lower().strip().rstrip(".")
    b = db_team.lower().strip().rstrip(".")
    if a == b:
        return True
    # Handle "St." vs "Saint" and other common variations
    a_clean = a.replace("st.", "st").replace("saint ", "st ")
    b_clean = b.replace("st.", "st").replace("saint ", "st ")
    return a_clean == b_clean


def _get_eliminated_team(game: dict) -> Optional[str]:
    """Return the name of the losing team in a final game, or None."""
    if game["status"] != "final":
        return None

    away = game.get("away", {})
    home = game.get("home", {})

    if home.get("winner"):
        return away.get("name")
    if away.get("winner"):
        return home.get("name")
    return None


def _empty_scores() -> dict:
    """Return an empty scores structure."""
    return {
        "last_updated": None,
        "round_dates": {r: dates for r, dates in zip(ROUND_ORDER, [
            ["2026-03-19", "2026-03-20"],
            ["2026-03-21", "2026-03-22"],
            ["2026-03-27", "2026-03-28"],
            ["2026-03-29", "2026-03-30"],
            ["2026-04-04"],
            ["2026-04-06"],
        ])},
        "scores": {},
        "eliminated_teams": [],
        "games_processed": [],
    }
