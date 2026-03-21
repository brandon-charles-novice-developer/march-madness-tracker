"""Shared fixtures for the scoring tracker test suite."""

import json
import os
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"


@pytest.fixture
def sample_players_db() -> list[dict]:
    """Minimal players database for unit tests."""
    return [
        {"name": "Kingston Flemings", "team": "Houston", "seed": 2, "region": "South", "ppg": 16.4, "status": "active", "role": "primary"},
        {"name": "Tyler Tanner", "team": "Vanderbilt", "seed": 5, "region": "South", "ppg": 19.2, "status": "active", "role": "primary"},
        {"name": "Tavari Johnson", "team": "Akron", "seed": 12, "region": "West", "ppg": 20.1, "status": "active", "role": "primary"},
        {"name": "Cameron Boozer", "team": "Duke", "seed": 1, "region": "East", "ppg": 22.5, "status": "active", "role": "primary"},
        {"name": "Robert Wright III", "team": "BYU", "seed": 6, "region": "West", "ppg": 18.2, "status": "active", "role": "primary"},
        {"name": "Labaron Philon Jr", "team": "Alabama", "seed": 4, "region": "Midwest", "ppg": 21.7, "status": "active", "role": "primary"},
        {"name": "Patrick Ngongba II", "team": "Duke", "seed": 1, "region": "East", "ppg": 10.7, "status": "active", "role": "tertiary"},
    ]


@pytest.fixture
def sample_draft_picks() -> list[dict]:
    """Minimal draft picks for unit tests."""
    return [
        {"overall_pick": 1, "round": 1, "manager": "Manager A", "player": "Kingston Flemings"},
        {"overall_pick": 2, "round": 1, "manager": "Manager A", "player": "Tyler Tanner"},
        {"overall_pick": 3, "round": 1, "manager": "Manager B", "player": "Cameron Boozer"},
        {"overall_pick": 4, "round": 1, "manager": "Manager B", "player": "Tavari Johnson"},
        {"overall_pick": 5, "round": 1, "manager": "Manager A", "player": "Robert Wright III"},
        {"overall_pick": 6, "round": 1, "manager": "Manager B", "player": "Labaron Philon Jr"},
    ]


@pytest.fixture
def sample_scores() -> dict:
    """Sample tournament scores state."""
    return {
        "last_updated": "2026-03-20T18:00:00",
        "scores": {
            "Kingston Flemings": {"R64": 18},
            "Tyler Tanner": {"R64": 26},
            "Cameron Boozer": {"R64": 22},
            "Tavari Johnson": {"R64": 4},
            "Robert Wright III": {"R64": 14},
            "Labaron Philon Jr": {"R64": 29},
        },
        "eliminated_teams": ["Akron", "BYU"],
        "games_processed": ["100", "101", "102"],
        "live_scores": {},
        "round_dates": {
            "R64": ["2026-03-19", "2026-03-20"],
            "R32": ["2026-03-21", "2026-03-22"],
        },
    }


@pytest.fixture
def sample_game() -> dict:
    """A single API game result with player stats."""
    return {
        "game_id": "999",
        "round": "R64",
        "date": "2026-03-20",
        "status": "final",
        "away": {"name": "Akron", "seed": 12, "score": 71, "winner": False},
        "home": {"name": "Texas Tech", "seed": 5, "score": 91, "winner": True},
        "player_stats": [
            {"first_name": "Tavari", "last_name": "Johnson", "team": "Akron", "points": 4, "minutes": "32"},
            {"first_name": "Some", "last_name": "Other", "team": "Texas Tech", "points": 20, "minutes": "35"},
        ],
    }


@pytest.fixture
def live_data_dir() -> Path:
    """Path to the actual data directory (for integration tests)."""
    return DATA_DIR


@pytest.fixture
def live_leaderboard(live_data_dir: Path) -> dict:
    """Load the actual leaderboard.json."""
    with open(live_data_dir / "leaderboard.json") as f:
        return json.load(f)


@pytest.fixture
def live_games(live_data_dir: Path) -> dict:
    """Load the actual games.json."""
    with open(live_data_dir / "games.json") as f:
        return json.load(f)


@pytest.fixture
def live_meta(live_data_dir: Path) -> dict:
    """Load the actual meta.json."""
    with open(live_data_dir / "meta.json") as f:
        return json.load(f)
