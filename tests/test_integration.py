"""Integration tests — validate live data integrity end-to-end.

These tests run against the actual data files in data/ to ensure
the full pipeline produced valid, consistent output.
"""

import json
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.mark.integration
class TestLeaderboardIntegrity:
    """Validate the leaderboard.json feed against business rules."""

    @pytest.fixture(autouse=True)
    def load_data(self):
        with open(DATA_DIR / "leaderboard.json") as f:
            self.lb = json.load(f)
        with open(DATA_DIR / "draft_state.json") as f:
            self.draft = json.load(f)
        with open(DATA_DIR / "players.json") as f:
            self.players_db = json.load(f)["players"]

    def test_has_ten_managers(self):
        assert len(self.lb["standings"]) == 10

    def test_all_managers_have_eight_players(self):
        for s in self.lb["standings"]:
            assert s["total_players"] == 8, f"{s['manager']} has {s['total_players']} players"

    def test_ranks_are_sequential(self):
        ranks = [s["rank"] for s in self.lb["standings"]]
        assert ranks == list(range(1, 11))

    def test_sorted_by_total_points_desc(self):
        points = [s["total_points"] for s in self.lb["standings"]]
        assert points == sorted(points, reverse=True)

    def test_active_players_lte_total(self):
        for s in self.lb["standings"]:
            assert s["active_players"] <= s["total_players"]

    def test_player_total_matches_round_sum(self):
        """Each player's total_points equals sum of their round_scores."""
        for s in self.lb["standings"]:
            for p in s["players"]:
                round_sum = sum(p["round_scores"].values())
                assert p["total_points"] == round_sum, (
                    f"{p['name']}: total={p['total_points']} but round sum={round_sum}"
                )

    def test_manager_total_matches_player_sum(self):
        """Each manager's total equals sum of their players' totals."""
        for s in self.lb["standings"]:
            player_sum = sum(p["total_points"] for p in s["players"])
            assert s["total_points"] == player_sum, (
                f"{s['manager']}: total={s['total_points']} but player sum={player_sum}"
            )

    def test_active_count_matches_status(self):
        """active_players count matches players with status='active'."""
        for s in self.lb["standings"]:
            active_count = sum(1 for p in s["players"] if p["status"] == "active")
            assert s["active_players"] == active_count, (
                f"{s['manager']}: active_players={s['active_players']} but counted={active_count}"
            )

    def test_all_draft_picks_accounted_for(self):
        """Every pick in draft_state.json appears in the leaderboard."""
        lb_players = set()
        for s in self.lb["standings"]:
            for p in s["players"]:
                lb_players.add(p["name"])

        for pick in self.draft["picks"]:
            assert pick["player"] in lb_players, (
                f"Draft pick {pick['player']} (#{pick['overall_pick']}) missing from leaderboard"
            )

    def test_eighty_total_players(self):
        total = sum(len(s["players"]) for s in self.lb["standings"])
        assert total == 80

    def test_eliminated_players_on_eliminated_teams(self):
        """Players marked 'eliminated' should be on teams in eliminated_teams."""
        # Load scores to get eliminated teams
        with open(DATA_DIR / "tournament_scores.json") as f:
            scores = json.load(f)
        eliminated_raw = set(scores.get("eliminated_teams", []))

        # Build normalized set for fuzzy matching
        import re
        def norm(name):
            n = name.lower().strip()
            n = re.sub(r"\s*\(.*?\)", "", n)
            n = n.rstrip(".").replace("'", "").replace(".", "")
            return re.sub(r"\s+", " ", n)

        eliminated_norm = {norm(t) for t in eliminated_raw}

        for s in self.lb["standings"]:
            for p in s["players"]:
                if p["status"] == "eliminated":
                    team_norm = norm(p["team"])
                    assert (
                        p["team"] in eliminated_raw or team_norm in eliminated_norm
                    ), f"{p['name']} marked eliminated but {p['team']} not in eliminated teams"

    def test_current_round_valid(self):
        assert self.lb["current_round"] in ["R64", "R32", "S16", "E8", "F4", "Championship"]

    def test_payouts_present(self):
        assert self.lb["payouts"]["first"] == 450
        assert self.lb["payouts"]["second"] == 50


@pytest.mark.integration
class TestGamesIntegrity:
    """Validate games.json feed."""

    @pytest.fixture(autouse=True)
    def load_data(self):
        with open(DATA_DIR / "games.json") as f:
            self.games = json.load(f)

    def test_has_games(self):
        assert len(self.games["games"]) > 0

    def test_r64_has_36_games(self):
        # 32 R64 games + 4 First Four games (counted as R64)
        r64 = [g for g in self.games["games"] if g["round"] == "R64"]
        assert len(r64) == 36

    def test_every_game_has_valid_status(self):
        valid = {"final", "live", "in_progress"}
        for g in self.games["games"]:
            assert g["status"] in valid, f"Game {g['game_id']}: status={g['status']}"

    def test_final_games_have_one_winner(self):
        for g in self.games["games"]:
            if g["status"] != "final":
                continue
            winners = []
            if g["away"]["winner"]:
                winners.append("away")
            if g["home"]["winner"]:
                winners.append("home")
            assert len(winners) == 1, f"Game {g['game_id']}: winners={winners}"

    def test_game_has_required_fields(self):
        for g in self.games["games"]:
            assert "game_id" in g
            assert "round" in g
            assert "date" in g
            assert "away" in g
            assert "home" in g
            assert "drafted_players" in g

    def test_drafted_players_have_manager(self):
        for g in self.games["games"]:
            for p in g["drafted_players"]:
                assert p["manager"] != "", f"Player {p['name']} has no manager"


@pytest.mark.integration
class TestMetaIntegrity:
    """Validate meta.json feed."""

    @pytest.fixture(autouse=True)
    def load_data(self):
        with open(DATA_DIR / "meta.json") as f:
            self.meta = json.load(f)

    def test_has_ten_managers(self):
        assert len(self.meta["managers"]) == 10

    def test_has_tournament_dates(self):
        assert len(self.meta["tournament_dates"]) == 6

    def test_pool_name(self):
        assert "March Madness" in self.meta["pool_name"]


@pytest.mark.integration
class TestCommentaryIntegrity:
    """Validate commentary.json feed."""

    @pytest.fixture(autouse=True)
    def load_data(self):
        with open(DATA_DIR / "commentary.json") as f:
            self.commentary = json.load(f)

    def test_has_all_ten_managers(self):
        assert len(self.commentary["managers"]) == 10

    def test_no_empty_blurbs(self):
        for manager, blurb in self.commentary["managers"].items():
            assert len(blurb) > 50, f"{manager} blurb is too short: {len(blurb)} chars"

    def test_has_gaygent_header(self):
        assert "Gaygent" in self.commentary["gaygent_header"] or "GAYGENT" in self.commentary["gaygent_header"]

    def test_has_hot_take(self):
        assert len(self.commentary["hot_take"]) > 20

    def test_has_bust_roast(self):
        assert len(self.commentary["bust_roast"]) > 20


@pytest.mark.integration
class TestScoresIntegrity:
    """Validate tournament_scores.json internal data."""

    @pytest.fixture(autouse=True)
    def load_data(self):
        with open(DATA_DIR / "tournament_scores.json") as f:
            self.scores = json.load(f)

    def test_has_scores(self):
        assert len(self.scores["scores"]) > 0

    def test_has_eliminated_teams(self):
        # After R64 + First Four, 36 teams eliminated (32 R64 + 4 First Four)
        assert len(self.scores["eliminated_teams"]) == 36

    def test_has_processed_games(self):
        # 32 R64 games + 4 First Four games
        assert len(self.scores["games_processed"]) == 36

    def test_all_scores_are_non_negative(self):
        for player, rounds in self.scores["scores"].items():
            for rnd, pts in rounds.items():
                assert pts >= 0, f"{player} has negative score in {rnd}: {pts}"
