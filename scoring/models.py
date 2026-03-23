"""Constants, type definitions, and round configuration."""

from typing import TypedDict

# Tournament round order
ROUND_ORDER: list[str] = ["R64", "R32", "S16", "E8", "F4", "Championship"]

# Game dates per round (2026 tournament)
# First Four (Mar 17-18) counts as R64 for scoring purposes
ROUND_DATES: dict[str, list[str]] = {
    "R64": ["2026-03-17", "2026-03-18", "2026-03-19", "2026-03-20"],
    "R32": ["2026-03-21", "2026-03-22"],
    "S16": ["2026-03-27", "2026-03-28"],
    "E8": ["2026-03-29", "2026-03-30"],
    "F4": ["2026-04-04"],
    "Championship": ["2026-04-06"],
}

# NCAA API bracketRound number → our round name
# bracketRound 1 = First Four (counts as R64 for scoring)
API_ROUND_MAP: dict[int, str] = {
    1: "R64",
    2: "R64",
    3: "R32",
    4: "S16",
    5: "E8",
    6: "F4",
    7: "Championship",
}

# Pool managers in draft order (position 1-10)
MANAGERS: list[str] = [
    "Josh Ehrlich",
    "Nick Reskin",
    "Mark Weiner",
    "Schaf Chulay",
    "Jordan Mackler",
    "AJ Spile",
    "Mike Haughey",
    "Alex Magged",
    "Brandon Nye",
    "Jake Pollack",
]

# Pool payouts
PAYOUTS: dict[str, int] = {"first": 450, "second": 50, "buy_in": 50}

# NCAA API base URL
API_BASE_URL = "https://ncaa-api.henrygd.me"

# Name suffixes to strip during player matching
NAME_SUFFIXES: list[str] = ["jr", "jr.", "sr", "sr.", "ii", "iii", "iv"]


class PlayerScore(TypedDict):
    """Per-player score entry in tournament_scores.json."""
    name: str
    team: str
    round_scores: dict[str, int]


class GameResult(TypedDict):
    """A single tournament game result."""
    game_id: str
    round: str
    date: str
    status: str
    away_name: str
    away_seed: int
    away_score: int
    away_winner: bool
    home_name: str
    home_seed: int
    home_score: int
    home_winner: bool
    player_stats: list[dict]


class ManagerStanding(TypedDict):
    """Manager standing in the leaderboard."""
    rank: int
    manager: str
    total_points: int
    active_players: int
    total_players: int
    round_totals: dict[str, int]
    players: list[dict]
