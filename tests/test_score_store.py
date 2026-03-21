"""Unit tests for scoring.score_store — persistence, matching, eliminations."""

import json
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest

from scoring.score_store import (
    _get_eliminated_team,
    _normalize_name,
    _teams_match,
    match_player,
    merge_round_scores,
)


class TestNormalizeName:
    def test_basic_name(self):
        assert _normalize_name("Kingston Flemings") == "kingston flemings"

    def test_strips_jr(self):
        assert _normalize_name("Labaron Philon Jr") == "labaron philon"

    def test_strips_jr_dot(self):
        assert _normalize_name("Labaron Philon Jr.") == "labaron philon"

    def test_strips_iii(self):
        assert _normalize_name("Robert Wright III") == "robert wright"

    def test_strips_ii(self):
        assert _normalize_name("Patrick Ngongba II") == "patrick ngongba"

    def test_handles_extra_whitespace(self):
        assert _normalize_name("  Kingston   Flemings  ") == "kingston flemings"

    def test_empty_string(self):
        assert _normalize_name("") == ""


class TestTeamsMatch:
    def test_exact_match(self):
        assert _teams_match("Houston", "Houston")

    def test_trailing_period(self):
        assert _teams_match("Ohio St.", "Ohio St")

    def test_saint_vs_st(self):
        assert _teams_match("Saint Mary's", "St Mary's")

    def test_different_teams(self):
        assert not _teams_match("Houston", "Duke")

    def test_case_insensitive(self):
        assert _teams_match("houston", "Houston")

    def test_parenthetical_stripped_in_normalize(self):
        # This is handled by feed_builder._normalize_team, not _teams_match
        # _teams_match does simpler normalization
        assert _teams_match("St. Mary's", "St Mary's")


class TestMatchPlayer:
    def test_exact_match(self, sample_players_db):
        drafted = {"Kingston Flemings", "Tyler Tanner"}
        result = match_player("Kingston", "Flemings", "Houston", sample_players_db, drafted)
        assert result == "Kingston Flemings"

    def test_suffix_match_jr(self, sample_players_db):
        drafted = {"Labaron Philon Jr"}
        result = match_player("Labaron", "Philon", "Alabama", sample_players_db, drafted)
        assert result == "Labaron Philon Jr"

    def test_suffix_match_iii(self, sample_players_db):
        drafted = {"Robert Wright III"}
        result = match_player("Robert", "Wright", "BYU", sample_players_db, drafted)
        assert result == "Robert Wright III"

    def test_suffix_match_ii(self, sample_players_db):
        drafted = {"Patrick Ngongba II"}
        result = match_player("Patrick", "Ngongba", "Duke", sample_players_db, drafted)
        assert result == "Patrick Ngongba II"

    def test_undrafted_player_returns_none(self, sample_players_db):
        drafted = {"Kingston Flemings"}
        result = match_player("Some", "Random", "Houston", sample_players_db, drafted)
        assert result is None

    def test_player_in_db_but_not_drafted(self, sample_players_db):
        drafted = set()  # nobody drafted
        result = match_player("Kingston", "Flemings", "Houston", sample_players_db, drafted)
        assert result is None

    def test_last_name_team_fallback(self, sample_players_db):
        drafted = {"Cameron Boozer"}
        # API might send "Cam" instead of "Cameron"
        result = match_player("Cam", "Boozer", "Duke", sample_players_db, drafted)
        assert result == "Cameron Boozer"


class TestGetEliminatedTeam:
    def test_away_team_loses(self):
        game = {
            "status": "final",
            "away": {"name": "Akron", "winner": False},
            "home": {"name": "Texas Tech", "winner": True},
        }
        assert _get_eliminated_team(game) == "Akron"

    def test_home_team_loses(self):
        game = {
            "status": "final",
            "away": {"name": "Duke", "winner": True},
            "home": {"name": "Siena", "winner": False},
        }
        assert _get_eliminated_team(game) == "Siena"

    def test_non_final_returns_none(self):
        game = {
            "status": "in_progress",
            "away": {"name": "Duke", "winner": False},
            "home": {"name": "Siena", "winner": False},
        }
        assert _get_eliminated_team(game) is None


class TestMergeRoundScores:
    def test_merges_new_game(self, sample_players_db, sample_draft_picks, sample_scores, sample_game):
        # sample_game has game_id "999" which is NOT in games_processed
        result = merge_round_scores(
            sample_scores, "R64", [sample_game], sample_players_db, sample_draft_picks
        )
        # Tavari Johnson should have R64 score updated (was 4, game adds 4 more)
        assert result["scores"]["Tavari Johnson"]["R64"] == 8  # 4 existing + 4 new
        assert "999" in result["games_processed"]

    def test_idempotent_skips_processed_games(self, sample_players_db, sample_draft_picks, sample_scores):
        game = {
            "game_id": "100",  # already in games_processed
            "round": "R64",
            "date": "2026-03-20",
            "status": "final",
            "away": {"name": "Test", "seed": 1, "score": 80, "winner": True},
            "home": {"name": "Test2", "seed": 16, "score": 60, "winner": False},
            "player_stats": [],
        }
        result = merge_round_scores(
            sample_scores, "R64", [game], sample_players_db, sample_draft_picks
        )
        # Scores should not change
        assert result["scores"] == sample_scores["scores"]

    def test_detects_elimination(self, sample_players_db, sample_draft_picks, sample_scores, sample_game):
        result = merge_round_scores(
            sample_scores, "R64", [sample_game], sample_players_db, sample_draft_picks
        )
        assert "Akron" in result["eliminated_teams"]

    def test_returns_new_dict_immutable(self, sample_players_db, sample_draft_picks, sample_scores, sample_game):
        result = merge_round_scores(
            sample_scores, "R64", [sample_game], sample_players_db, sample_draft_picks
        )
        assert result is not sample_scores
        # Original should be unchanged
        assert "999" not in sample_scores["games_processed"]

    def test_live_game_updates_scores(self, sample_players_db, sample_draft_picks, sample_scores):
        game = {
            "game_id": "998",
            "round": "R64",
            "date": "2026-03-20",
            "status": "live",
            "away": {"name": "Houston", "seed": 2, "score": 40, "winner": False},
            "home": {"name": "Test2", "seed": 15, "score": 30, "winner": False},
            "player_stats": [
                {"first_name": "Kingston", "last_name": "Flemings", "team": "Houston", "points": 10},
            ],
        }
        result = merge_round_scores(
            sample_scores, "R64", [game], sample_players_db, sample_draft_picks
        )
        # Live game should update scores but NOT mark as processed
        assert "998" not in result["games_processed"]
        assert result["scores"]["Kingston Flemings"]["R64"] == 28  # 18 + 10
        assert result["live_scores"]["998:Kingston Flemings"] == 10

    def test_live_then_final_locks_score(self, sample_players_db, sample_draft_picks, sample_scores):
        # First sync: live game with 10 pts
        live_game = {
            "game_id": "998",
            "round": "R64",
            "date": "2026-03-20",
            "status": "live",
            "away": {"name": "Houston", "seed": 2, "score": 40, "winner": False},
            "home": {"name": "Test2", "seed": 15, "score": 30, "winner": False},
            "player_stats": [
                {"first_name": "Kingston", "last_name": "Flemings", "team": "Houston", "points": 10},
            ],
        }
        after_live = merge_round_scores(
            sample_scores, "R64", [live_game], sample_players_db, sample_draft_picks
        )
        assert after_live["scores"]["Kingston Flemings"]["R64"] == 28  # 18 + 10

        # Second sync: same game now final with 15 pts
        final_game = {
            **live_game,
            "status": "final",
            "home": {"name": "Test2", "seed": 15, "score": 60, "winner": False},
            "away": {"name": "Houston", "seed": 2, "score": 80, "winner": True},
            "player_stats": [
                {"first_name": "Kingston", "last_name": "Flemings", "team": "Houston", "points": 15},
            ],
        }
        after_final = merge_round_scores(
            after_live, "R64", [final_game], sample_players_db, sample_draft_picks
        )
        # Should replace live 10 with final 15: 18 + 15 = 33
        assert after_final["scores"]["Kingston Flemings"]["R64"] == 33
        assert "998" in after_final["games_processed"]
        # Live tracking cleaned up
        assert "998:Kingston Flemings" not in after_final["live_scores"]

    def test_live_score_updates_on_subsequent_syncs(self, sample_players_db, sample_draft_picks, sample_scores):
        # First sync: 5 pts
        game_v1 = {
            "game_id": "998",
            "round": "R64",
            "date": "2026-03-20",
            "status": "live",
            "away": {"name": "Houston", "seed": 2, "score": 20, "winner": False},
            "home": {"name": "Test2", "seed": 15, "score": 15, "winner": False},
            "player_stats": [
                {"first_name": "Kingston", "last_name": "Flemings", "team": "Houston", "points": 5},
            ],
        }
        after_v1 = merge_round_scores(
            sample_scores, "R64", [game_v1], sample_players_db, sample_draft_picks
        )
        assert after_v1["scores"]["Kingston Flemings"]["R64"] == 23  # 18 + 5

        # Second sync: now 12 pts (scored 7 more)
        game_v2 = {**game_v1, "player_stats": [
            {"first_name": "Kingston", "last_name": "Flemings", "team": "Houston", "points": 12},
        ]}
        after_v2 = merge_round_scores(
            after_v1, "R64", [game_v2], sample_players_db, sample_draft_picks
        )
        # Should be 18 (pre-existing) + 12 (latest live) = 30
        assert after_v2["scores"]["Kingston Flemings"]["R64"] == 30
        assert after_v2["live_scores"]["998:Kingston Flemings"] == 12
