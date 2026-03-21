"""Build structured JSON feeds for the GitHub Pages frontend.

Produces 3 files in site/data/:
  - leaderboard.json  (standings + per-manager player details)
  - games.json        (game-level results with drafted player highlights)
  - meta.json         (static pool metadata)
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from scoring.models import MANAGERS, PAYOUTS, ROUND_DATES, ROUND_ORDER

SITE_DATA_DIR = Path(__file__).parent.parent / "data"


def build_leaderboard_feed(
    draft_picks: list[dict],
    scores: dict,
    players_db: list[dict],
) -> dict:
    """Build the leaderboard.json feed.

    Contains ranked standings with per-manager player breakdowns.
    """
    player_scores = scores.get("scores", {})
    raw_eliminated = scores.get("eliminated_teams", [])
    eliminated_teams = set(raw_eliminated)
    # Also store normalized versions for fuzzy matching
    eliminated_normalized = {_normalize_team(t) for t in raw_eliminated}

    # Build player lookup from players_db
    player_info = _build_player_info(players_db)

    # Build manager → picks mapping
    manager_picks = _group_picks_by_manager(draft_picks)

    # Determine current round
    current_round = _detect_current_round(player_scores)

    # Build standings
    standings = []
    for manager in MANAGERS:
        picks = manager_picks.get(manager, [])
        players = []
        total_points = 0
        active_count = 0
        round_totals: dict[str, int] = {r: 0 for r in ROUND_ORDER}

        for pick in picks:
            player_name = pick["player"]
            info = player_info.get(player_name, {})
            team = info.get("team", "")
            is_active = (
                team not in eliminated_teams
                and _normalize_team(team) not in eliminated_normalized
            )

            p_scores = player_scores.get(player_name, {})
            p_total = sum(p_scores.values())
            total_points += p_total

            if is_active:
                active_count += 1

            for rnd, pts in p_scores.items():
                if rnd in round_totals:
                    round_totals[rnd] += pts

            players.append({
                "name": player_name,
                "team": team,
                "seed": info.get("seed", 0),
                "region": info.get("region", ""),
                "pick": pick["overall_pick"],
                "draft_round": pick["round"],
                "status": "active" if is_active else "eliminated",
                "total_points": p_total,
                "round_scores": dict(p_scores),
                "ppg_season": info.get("ppg", 0),
            })

        # Sort players by total points desc
        players.sort(key=lambda p: p["total_points"], reverse=True)

        standings.append({
            "rank": 0,  # assigned after sorting
            "manager": manager,
            "total_points": total_points,
            "active_players": active_count,
            "total_players": len(picks),
            "round_totals": round_totals,
            "players": players,
        })

    # Sort by total points desc, assign ranks
    standings.sort(key=lambda s: s["total_points"], reverse=True)
    for i, standing in enumerate(standings):
        standing["rank"] = i + 1

    return {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "current_round": current_round,
        "tournament_status": _tournament_status(current_round, eliminated_teams),
        "payouts": PAYOUTS,
        "rounds": ROUND_ORDER,
        "standings": standings,
    }


def build_games_feed(
    games_data: list[dict],
    draft_picks: list[dict],
    players_db: list[dict],
) -> dict:
    """Build the games.json feed.

    Contains game-level results with drafted player highlights.
    """
    # Build player → manager lookup from draft picks
    player_manager = {pick["player"]: pick["manager"] for pick in draft_picks}
    drafted_names = set(player_manager.keys())

    # Build player info lookup
    player_info = _build_player_info(players_db)

    games_out = []
    for game in games_data:
        drafted_players = []
        for ps in game.get("player_stats", []):
            full_name = f"{ps.get('first_name', '')} {ps.get('last_name', '')}".strip()

            # Check if this player was drafted (by matching against drafted names)
            matched = _find_drafted_match(full_name, ps.get("team", ""), drafted_names, player_info)
            if matched:
                drafted_players.append({
                    "name": matched,
                    "team": ps.get("team", ""),
                    "manager": player_manager.get(matched, ""),
                    "points": ps.get("points", 0),
                    "minutes": ps.get("minutes", "0"),
                    "fg": ps.get("fg", "0/0"),
                    "three": ps.get("three", "0/0"),
                    "ft": ps.get("ft", "0/0"),
                    "rebounds": ps.get("rebounds", 0),
                    "assists": ps.get("assists", 0),
                })

        games_out.append({
            "game_id": game["game_id"],
            "round": game["round"],
            "date": game["date"],
            "status": game["status"],
            "away": game["away"],
            "home": game["home"],
            "drafted_players": drafted_players,
        })

    # Sort by date desc, then game_id
    games_out.sort(key=lambda g: (g["date"], g["game_id"]), reverse=True)

    return {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "games": games_out,
    }


def build_meta_feed() -> dict:
    """Build the meta.json feed (static pool metadata)."""
    return {
        "pool_name": "March Madness 2026",
        "format": "Player draft — points scored by your players count toward your total",
        "draft_type": "Serpentine, 10 teams, 8 rounds",
        "managers": MANAGERS,
        "payouts": PAYOUTS,
        "tournament_dates": ROUND_DATES,
    }


def write_feeds(
    leaderboard: dict,
    games: dict,
    meta: dict,
) -> None:
    """Write all 3 JSON feeds to site/data/."""
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    for name, data in [
        ("leaderboard.json", leaderboard),
        ("games.json", games),
        ("meta.json", meta),
    ]:
        path = SITE_DATA_DIR / name
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"  Wrote {path}")


# --- Helpers ---


def _normalize_team(name: str) -> str:
    """Normalize team name for fuzzy elimination matching.

    Handles: 'Ohio St.' vs 'Ohio St', 'Saint Mary's (CA)' vs 'Saint Mary's',
    'South Fla.' vs 'South Florida', 'St. John's (NY)' vs 'St Johns'.
    """
    import re
    n = name.lower().strip()
    n = re.sub(r"\s*\(.*?\)", "", n)  # strip parentheticals: (CA), (NY), (OH), (FL)
    n = n.rstrip(".")                  # trailing period
    n = n.replace("'", "")            # apostrophes
    n = n.replace(".", "")            # remaining dots
    n = re.sub(r"\s+", " ", n)        # collapse whitespace
    return n


def _build_player_info(players_db: list[dict]) -> dict[str, dict]:
    """Build name → {team, seed, region, ppg} lookup from players_db."""
    return {
        p["name"]: {
            "team": p.get("team", ""),
            "seed": p.get("seed", 0),
            "region": p.get("region", ""),
            "ppg": p.get("ppg", 0),
        }
        for p in players_db
    }


def _group_picks_by_manager(draft_picks: list[dict]) -> dict[str, list[dict]]:
    """Group draft picks by manager name."""
    grouped: dict[str, list[dict]] = {}
    for pick in draft_picks:
        manager = pick["manager"]
        if manager not in grouped:
            grouped[manager] = []
        grouped[manager].append(pick)
    return grouped


def _detect_current_round(player_scores: dict) -> str:
    """Determine the latest round that has any scores."""
    latest = "R64"
    for round_name in ROUND_ORDER:
        for p_scores in player_scores.values():
            if isinstance(p_scores, dict) and round_name in p_scores:
                latest = round_name
                break
    return latest


def _tournament_status(current_round: str, eliminated_teams: set) -> str:
    """Determine overall tournament status."""
    if current_round == "Championship" and len(eliminated_teams) >= 63:
        return "complete"
    if len(eliminated_teams) == 0:
        return "not_started"
    return "in_progress"


def _find_drafted_match(
    full_name: str,
    team: str,
    drafted_names: set[str],
    player_info: dict[str, dict],
) -> "str | None":
    """Find a drafted player matching an API player name."""
    name_lower = full_name.lower().strip()

    for drafted in drafted_names:
        if drafted.lower().strip() == name_lower:
            return drafted

    # Try matching by last name + team
    api_last = name_lower.split()[-1] if name_lower.split() else ""
    for drafted in drafted_names:
        parts = drafted.lower().split()
        drafted_last = parts[-1] if parts else ""
        if drafted_last == api_last:
            info = player_info.get(drafted, {})
            if info.get("team", "").lower() == team.lower():
                return drafted

    return None
