"""CLI interface for the scoring tracker.

Usage:
    python -m scoring sync [--round R64]     Pull scores from NCAA API
    python -m scoring build                  Rebuild feeds from local data
    python -m scoring status                 Show current standings
    python -m scoring score NAME ROUND PTS   Manual score override
    python -m scoring eliminate TEAM ROUND   Mark team as eliminated
"""

import argparse

from scoring.feed_builder import (
    build_games_feed,
    build_leaderboard_feed,
    build_meta_feed,
    write_feeds,
)
from scoring.models import ROUND_ORDER
from scoring.ncaa_api import fetch_round_games
from scoring.score_store import (
    load_draft_picks,
    load_games,
    load_players_db,
    load_scores,
    merge_round_scores,
    save_games,
    save_scores,
)


def cmd_sync(args: argparse.Namespace) -> None:
    """Pull scores from NCAA API and rebuild feeds."""
    scores = load_scores()
    players_db = load_players_db()
    draft_picks = load_draft_picks()

    rounds_to_sync = [args.round] if args.round else _played_rounds(scores)
    all_games: list[dict] = []

    for round_name in rounds_to_sync:
        print(f"\n=== Syncing {round_name} ===")
        games = fetch_round_games(round_name)
        if not games:
            print(f"  No games found for {round_name}")
            continue

        scores = merge_round_scores(scores, round_name, games, players_db, draft_picks)
        all_games.extend(games)

        final_count = sum(1 for g in games if g["status"] == "final")
        print(f"  Processed {final_count} final games")

    save_scores(scores)

    # Merge new games with previously saved games
    existing_games = load_games()
    existing_ids = {g["game_id"] for g in existing_games}
    merged_games = existing_games + [g for g in all_games if g["game_id"] not in existing_ids]
    save_games(merged_games)

    _rebuild_feeds(scores, merged_games, draft_picks, players_db)
    _print_standings(scores, draft_picks, players_db)


def cmd_build(_args: argparse.Namespace) -> None:
    """Rebuild feeds from local tournament_scores.json."""
    scores = load_scores()
    draft_picks = load_draft_picks()
    players_db = load_players_db()

    games = load_games()
    _rebuild_feeds(scores, games, draft_picks, players_db)
    print(f"\nFeeds rebuilt from local data ({len(games)} games).")


def cmd_status(_args: argparse.Namespace) -> None:
    """Show current standings in terminal."""
    scores = load_scores()
    draft_picks = load_draft_picks()
    players_db = load_players_db()
    _print_standings(scores, draft_picks, players_db)


def cmd_score(args: argparse.Namespace) -> None:
    """Manually set a player's score for a round."""
    scores = load_scores()
    player_scores = dict(scores.get("scores", {}))

    existing = dict(player_scores.get(args.name, {}))
    existing[args.round_name] = args.points
    player_scores[args.name] = existing

    updated = {**scores, "scores": player_scores}
    save_scores(updated)

    draft_picks = load_draft_picks()
    players_db = load_players_db()
    _rebuild_feeds(updated, [], draft_picks, players_db)
    print(f"  Set {args.name} {args.round_name} = {args.points}")


def cmd_eliminate(args: argparse.Namespace) -> None:
    """Mark a team as eliminated."""
    scores = load_scores()
    eliminated = list(scores.get("eliminated_teams", []))

    if args.team not in eliminated:
        eliminated.append(args.team)
        eliminated.sort()

    updated = {**scores, "eliminated_teams": eliminated}
    save_scores(updated)

    draft_picks = load_draft_picks()
    players_db = load_players_db()
    _rebuild_feeds(updated, [], draft_picks, players_db)
    print(f"  Eliminated: {args.team}")


def _rebuild_feeds(
    scores: dict,
    games: list[dict],
    draft_picks: list[dict],
    players_db: list[dict],
) -> None:
    """Build and write all JSON feeds."""
    print("\nBuilding feeds...")
    leaderboard = build_leaderboard_feed(draft_picks, scores, players_db)
    games_feed = build_games_feed(games, draft_picks, players_db)
    meta = build_meta_feed()
    write_feeds(leaderboard, games_feed, meta)


def _print_standings(
    scores: dict,
    draft_picks: list[dict],
    players_db: list[dict],
) -> None:
    """Print a compact leaderboard to terminal."""
    leaderboard = build_leaderboard_feed(draft_picks, scores, players_db)

    print(f"\n{'='*60}")
    print(f"  MARCH MADNESS 2026 — {leaderboard['current_round']}")
    print(f"{'='*60}")
    print(f"{'Rank':<5} {'Manager':<20} {'Total':>6} {'Active':>8}")
    print(f"{'-'*5} {'-'*20} {'-'*6} {'-'*8}")

    for s in leaderboard["standings"]:
        active = f"{s['active_players']}/{s['total_players']}"
        print(f"{s['rank']:<5} {s['manager']:<20} {s['total_points']:>6} {active:>8}")

    eliminated = scores.get("eliminated_teams", [])
    print(f"\nEliminated teams ({len(eliminated)}): {', '.join(eliminated) or 'none'}")


def _played_rounds(scores: dict) -> list[str]:
    """Determine which rounds to sync based on tournament dates.

    Only returns rounds that have game dates on or before today
    AND are not fully complete (still have live or unprocessed games).
    A round is considered complete when all its game dates have passed
    and the last date was more than 1 day ago.
    """
    from datetime import date, timedelta

    from scoring.models import ROUND_DATES

    today = date.today()
    today_str = today.isoformat()
    yesterday = (today - timedelta(days=1)).isoformat()
    rounds = []
    for round_name in ROUND_ORDER:
        dates = ROUND_DATES.get(round_name, [])
        if not dates or dates[0] > today_str:
            continue
        # Skip rounds where ALL dates are before yesterday (fully done)
        last_date = dates[-1]
        if last_date <= yesterday:
            continue
        rounds.append(round_name)
    return rounds


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="scoring",
        description="March Madness 2026 — Scoring Tracker",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # sync
    sync_parser = subparsers.add_parser("sync", help="Pull scores from NCAA API")
    sync_parser.add_argument("--round", dest="round", choices=ROUND_ORDER, default=None)
    sync_parser.set_defaults(func=cmd_sync)

    # build
    build_parser = subparsers.add_parser("build", help="Rebuild feeds from local data")
    build_parser.set_defaults(func=cmd_build)

    # status
    status_parser = subparsers.add_parser("status", help="Show current standings")
    status_parser.set_defaults(func=cmd_status)

    # score
    score_parser = subparsers.add_parser("score", help="Manual score override")
    score_parser.add_argument("name", help="Player name")
    score_parser.add_argument("round_name", choices=ROUND_ORDER, help="Round")
    score_parser.add_argument("points", type=int, help="Points scored")
    score_parser.set_defaults(func=cmd_score)

    # eliminate
    elim_parser = subparsers.add_parser("eliminate", help="Mark team as eliminated")
    elim_parser.add_argument("team", help="Team name")
    elim_parser.set_defaults(func=cmd_eliminate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
