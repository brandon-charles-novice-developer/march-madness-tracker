"""Unit + integration tests for scoring.ncaa_api — NCAA API client."""

import pytest

from scoring.ncaa_api import _parse_int, fetch_boxscore, fetch_scoreboard


class TestParseInt:
    def test_valid_int(self):
        assert _parse_int("42") == 42

    def test_zero(self):
        assert _parse_int("0") == 0

    def test_empty_string(self):
        assert _parse_int("") == 0

    def test_none(self):
        assert _parse_int(None) == 0

    def test_non_numeric(self):
        assert _parse_int("abc") == 0


@pytest.mark.integration
class TestFetchScoreboard:
    """Integration tests — hit the real NCAA API."""

    def test_fetch_r64_day1(self):
        games = fetch_scoreboard("2026-03-19")
        assert len(games) > 0
        game = games[0]
        assert "game_id" in game
        assert "round" in game
        assert "away" in game
        assert "home" in game
        assert game["round"] == "R64"

    def test_game_has_team_names(self):
        games = fetch_scoreboard("2026-03-19")
        for game in games:
            assert game["away"]["name"] != ""
            assert game["home"]["name"] != ""

    def test_game_has_seeds(self):
        games = fetch_scoreboard("2026-03-19")
        for game in games:
            assert isinstance(game["away"]["seed"], int)
            assert isinstance(game["home"]["seed"], int)

    def test_no_games_on_off_day(self):
        games = fetch_scoreboard("2026-01-01")
        tournament_games = [g for g in games if g["round"] == "R64"]
        assert len(tournament_games) == 0


@pytest.mark.integration
class TestFetchBoxscore:
    """Integration tests — hit the real NCAA API."""

    def test_fetch_valid_game(self):
        # Akron vs Texas Tech (R64, Mar 20)
        result = fetch_boxscore("6534622")
        assert result["game_id"] == "6534622"
        assert len(result["teams"]) == 2

    def test_boxscore_has_players(self):
        result = fetch_boxscore("6534622")
        for team in result["teams"]:
            assert len(team["players"]) > 0

    def test_player_has_stats(self):
        result = fetch_boxscore("6534622")
        for team in result["teams"]:
            for player in team["players"]:
                assert "first_name" in player
                assert "last_name" in player
                assert "points" in player
                assert isinstance(player["points"], int)

    def test_tavari_johnson_in_akron_boxscore(self):
        result = fetch_boxscore("6534622")
        akron_team = [t for t in result["teams"] if t["name"] == "Akron"]
        assert len(akron_team) == 1
        johnsons = [
            p for p in akron_team[0]["players"]
            if p["last_name"] == "Johnson" and p["first_name"] == "Tavari"
        ]
        assert len(johnsons) == 1
        assert johnsons[0]["points"] == 4

    def test_invalid_game_returns_empty(self):
        result = fetch_boxscore("0000000")
        assert result["teams"] == []
