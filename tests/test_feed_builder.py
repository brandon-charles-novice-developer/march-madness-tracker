"""Unit tests for scoring.feed_builder — JSON feed generation."""

import pytest

from scoring.feed_builder import (
    _detect_current_round,
    _find_drafted_match,
    _normalize_team,
    build_games_feed,
    build_leaderboard_feed,
    build_meta_feed,
)
from scoring.models import MANAGERS, PAYOUTS, ROUND_ORDER


class TestNormalizeTeam:
    def test_strips_parenthetical(self):
        assert _normalize_team("Saint Mary's (CA)") == "saint marys"

    def test_strips_trailing_period(self):
        assert _normalize_team("Ohio St.") == "ohio st"

    def test_strips_apostrophe(self):
        assert _normalize_team("St. John's") == "st johns"

    def test_ohio_st_matches(self):
        assert _normalize_team("Ohio St.") == _normalize_team("Ohio St")

    def test_saint_marys_matches(self):
        assert _normalize_team("Saint Mary's (CA)") == _normalize_team("Saint Mary's")

    def test_plain_name_unchanged(self):
        assert _normalize_team("Houston") == "houston"


class TestDetectCurrentRound:
    def test_r64_scores_only(self):
        scores = {"Player A": {"R64": 10}}
        assert _detect_current_round(scores) == "R64"

    def test_r32_scores_present(self):
        scores = {"Player A": {"R64": 10, "R32": 15}}
        assert _detect_current_round(scores) == "R32"

    def test_empty_scores(self):
        assert _detect_current_round({}) == "R64"

    def test_championship_scores(self):
        scores = {"Player A": {"R64": 10, "R32": 15, "S16": 20, "E8": 18, "F4": 22, "Championship": 25}}
        assert _detect_current_round(scores) == "Championship"


class TestFindDraftedMatch:
    def test_exact_match(self):
        drafted = {"Kingston Flemings"}
        info = {"Kingston Flemings": {"team": "Houston"}}
        assert _find_drafted_match("Kingston Flemings", "Houston", drafted, info) == "Kingston Flemings"

    def test_case_insensitive(self):
        drafted = {"Kingston Flemings"}
        info = {"Kingston Flemings": {"team": "Houston"}}
        assert _find_drafted_match("kingston flemings", "Houston", drafted, info) == "Kingston Flemings"

    def test_last_name_team_match(self):
        drafted = {"Kingston Flemings"}
        info = {"Kingston Flemings": {"team": "Houston"}}
        assert _find_drafted_match("K. Flemings", "Houston", drafted, info) == "Kingston Flemings"

    def test_no_match(self):
        drafted = {"Kingston Flemings"}
        info = {"Kingston Flemings": {"team": "Houston"}}
        assert _find_drafted_match("Nobody Here", "Duke", drafted, info) is None


class TestBuildLeaderboardFeed:
    def test_has_required_keys(self, sample_draft_picks, sample_scores, sample_players_db):
        feed = build_leaderboard_feed(sample_draft_picks, sample_scores, sample_players_db)
        assert "standings" in feed
        assert "current_round" in feed
        assert "tournament_status" in feed
        assert "payouts" in feed
        assert "rounds" in feed
        assert "last_updated" in feed

    def test_standings_sorted_by_points(self, sample_draft_picks, sample_scores, sample_players_db):
        feed = build_leaderboard_feed(sample_draft_picks, sample_scores, sample_players_db)
        points = [s["total_points"] for s in feed["standings"]]
        assert points == sorted(points, reverse=True)

    def test_ranks_assigned(self, sample_draft_picks, sample_scores, sample_players_db):
        feed = build_leaderboard_feed(sample_draft_picks, sample_scores, sample_players_db)
        ranks = [s["rank"] for s in feed["standings"]]
        assert ranks == list(range(1, len(ranks) + 1))  # sequential from 1

    def test_active_player_count(self, sample_draft_picks, sample_scores, sample_players_db):
        feed = build_leaderboard_feed(sample_draft_picks, sample_scores, sample_players_db)
        for standing in feed["standings"]:
            if standing["manager"] == "Manager A":
                # Flemings (Houston active), Tanner (Vandy active), Wright III (BYU eliminated)
                assert standing["active_players"] == 2
                assert standing["total_players"] == 3

    def test_eliminated_players_marked(self, sample_draft_picks, sample_scores, sample_players_db):
        feed = build_leaderboard_feed(sample_draft_picks, sample_scores, sample_players_db)
        for standing in feed["standings"]:
            for player in standing["players"]:
                if player["name"] == "Tavari Johnson":
                    assert player["status"] == "eliminated"
                if player["name"] == "Kingston Flemings":
                    assert player["status"] == "active"

    def test_player_round_scores_present(self, sample_draft_picks, sample_scores, sample_players_db):
        feed = build_leaderboard_feed(sample_draft_picks, sample_scores, sample_players_db)
        for standing in feed["standings"]:
            for player in standing["players"]:
                if player["name"] == "Tyler Tanner":
                    assert player["round_scores"]["R64"] == 26
                    assert player["total_points"] == 26


class TestBuildMetaFeed:
    def test_has_pool_name(self):
        meta = build_meta_feed()
        assert meta["pool_name"] == "March Madness 2026"

    def test_has_all_managers(self):
        meta = build_meta_feed()
        assert len(meta["managers"]) == 10
        assert meta["managers"] == MANAGERS

    def test_has_payouts(self):
        meta = build_meta_feed()
        assert meta["payouts"] == PAYOUTS

    def test_has_tournament_dates(self):
        meta = build_meta_feed()
        assert "R64" in meta["tournament_dates"]
        assert "Championship" in meta["tournament_dates"]


class TestBuildGamesFeed:
    def test_empty_games(self, sample_draft_picks, sample_players_db):
        feed = build_games_feed([], sample_draft_picks, sample_players_db)
        assert feed["games"] == []
        assert "last_updated" in feed

    def test_drafted_players_highlighted(self, sample_draft_picks, sample_players_db, sample_game):
        feed = build_games_feed([sample_game], sample_draft_picks, sample_players_db)
        assert len(feed["games"]) == 1
        game = feed["games"][0]
        drafted = [p for p in game["drafted_players"] if p["name"] == "Tavari Johnson"]
        assert len(drafted) == 1
        assert drafted[0]["manager"] == "Manager B"
        assert drafted[0]["points"] == 4
