"""End-to-end tests — validate the full pipeline and frontend contract.

These tests verify that running the scoring pipeline produces output
that the frontend can consume correctly.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"


@pytest.mark.e2e
class TestFullPipeline:
    """Run the CLI and verify output end-to-end."""

    def test_status_command_runs(self):
        result = subprocess.run(
            [sys.executable, "-m", "scoring", "status"],
            cwd=str(REPO_ROOT),
            env={"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin"},
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "MARCH MADNESS 2026" in result.stdout
        assert "Brandon Nye" in result.stdout

    def test_build_command_produces_feeds(self):
        result = subprocess.run(
            [sys.executable, "-m", "scoring", "build"],
            cwd=str(REPO_ROOT),
            env={"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin"},
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "leaderboard.json" in result.stdout
        assert "games.json" in result.stdout
        assert "meta.json" in result.stdout

    def test_build_output_is_valid_json(self):
        subprocess.run(
            [sys.executable, "-m", "scoring", "build"],
            cwd=str(REPO_ROOT),
            env={"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin"},
            capture_output=True, text=True, timeout=10,
        )
        for filename in ["leaderboard.json", "games.json", "meta.json"]:
            path = DATA_DIR / filename
            assert path.exists(), f"{filename} not found"
            with open(path) as f:
                data = json.load(f)
            assert isinstance(data, dict)


@pytest.mark.e2e
class TestFrontendContract:
    """Verify the JSON feeds satisfy the frontend's expectations.

    These tests encode what index.html's JavaScript assumes about
    the data structure — if any of these fail, the frontend will break.
    """

    @pytest.fixture(autouse=True)
    def load_feeds(self):
        with open(DATA_DIR / "leaderboard.json") as f:
            self.lb = json.load(f)
        with open(DATA_DIR / "meta.json") as f:
            self.meta = json.load(f)
        with open(DATA_DIR / "commentary.json") as f:
            self.commentary = json.load(f)

    def test_leaderboard_standings_is_list(self):
        """JS: lb.standings.slice(0, 3) — must be array."""
        assert isinstance(self.lb["standings"], list)

    def test_standings_have_rank_and_manager(self):
        """JS: s.rank, s.manager — used in renderPodium and renderManagerCards."""
        for s in self.lb["standings"]:
            assert isinstance(s["rank"], int)
            assert isinstance(s["manager"], str)
            assert len(s["manager"]) > 0

    def test_standings_have_points_and_active(self):
        """JS: s.total_points, s.active_players, s.total_players."""
        for s in self.lb["standings"]:
            assert isinstance(s["total_points"], int)
            assert isinstance(s["active_players"], int)
            assert isinstance(s["total_players"], int)

    def test_standings_have_players_array(self):
        """JS: s.players.filter(p => p.status === 'active')."""
        for s in self.lb["standings"]:
            assert isinstance(s["players"], list)
            for p in s["players"]:
                assert p["status"] in ("active", "eliminated")

    def test_players_have_round_scores(self):
        """JS: p.round_scores[currentRound] — must be dict."""
        for s in self.lb["standings"]:
            for p in s["players"]:
                assert isinstance(p["round_scores"], dict)

    def test_players_have_total_points(self):
        """JS: p.total_points — used for sorting."""
        for s in self.lb["standings"]:
            for p in s["players"]:
                assert isinstance(p["total_points"], int)

    def test_players_have_team_and_seed(self):
        """JS: p.team, p.seed — displayed in player table."""
        for s in self.lb["standings"]:
            for p in s["players"]:
                assert isinstance(p["team"], str)
                assert isinstance(p["seed"], int)

    def test_players_have_ppg_season(self):
        """JS: p.ppg_season — used for bust calculation."""
        for s in self.lb["standings"]:
            for p in s["players"]:
                assert "ppg_season" in p

    def test_leaderboard_has_current_round(self):
        """JS: lb.current_round — used in renderHighlights."""
        assert isinstance(self.lb["current_round"], str)

    def test_leaderboard_has_rounds_array(self):
        """JS: lb.rounds — used in renderManagerCards for column headers."""
        assert isinstance(self.lb["rounds"], list)
        assert len(self.lb["rounds"]) == 6

    def test_leaderboard_has_last_updated(self):
        """JS: new Date(lb.last_updated) — must be parseable."""
        assert isinstance(self.lb["last_updated"], str)
        assert len(self.lb["last_updated"]) > 10

    def test_meta_has_tournament_dates(self):
        """JS: meta.tournament_dates — used in scheduleRefresh."""
        assert isinstance(self.meta["tournament_dates"], dict)
        for dates in self.meta["tournament_dates"].values():
            assert isinstance(dates, list)

    def test_commentary_has_managers_dict(self):
        """JS: commentary.managers[s.manager] — keyed by manager name."""
        assert isinstance(self.commentary["managers"], dict)

    def test_commentary_has_bust_roast(self):
        """JS: commentary.bust_roast — displayed in bust section."""
        assert isinstance(self.commentary["bust_roast"], str)

    def test_commentary_has_gaygent_header(self):
        """JS: commentary.gaygent_header — displayed in subtitle."""
        assert isinstance(self.commentary["gaygent_header"], str)

    def test_commentary_manager_keys_match_leaderboard(self):
        """Commentary must have an entry for every manager in standings."""
        lb_managers = {s["manager"] for s in self.lb["standings"]}
        commentary_managers = set(self.commentary["managers"].keys())
        missing = lb_managers - commentary_managers
        assert not missing, f"Commentary missing for: {missing}"


@pytest.mark.e2e
class TestGitHubPagesContract:
    """Verify the deployed site serves correct data."""

    @pytest.fixture(autouse=True)
    def check_connectivity(self):
        """Skip if GitHub Pages is unreachable."""
        import urllib.request
        try:
            urllib.request.urlopen(
                "https://brandon-charles-novice-developer.github.io/march-madness-tracker/data/meta.json",
                timeout=5,
            )
        except Exception:
            pytest.skip("GitHub Pages not reachable")

    def test_index_html_served(self):
        import urllib.request
        resp = urllib.request.urlopen(
            "https://brandon-charles-novice-developer.github.io/march-madness-tracker/"
        )
        html = resp.read().decode()
        assert "Gaygent" in html
        assert "leaderboard.json" in html

    def test_leaderboard_json_served(self):
        import urllib.request
        resp = urllib.request.urlopen(
            "https://brandon-charles-novice-developer.github.io/march-madness-tracker/data/leaderboard.json"
        )
        data = json.loads(resp.read())
        assert len(data["standings"]) == 10

    def test_meta_json_served(self):
        import urllib.request
        resp = urllib.request.urlopen(
            "https://brandon-charles-novice-developer.github.io/march-madness-tracker/data/meta.json"
        )
        data = json.loads(resp.read())
        assert data["pool_name"] == "March Madness 2026"

    def test_commentary_json_served(self):
        import urllib.request
        resp = urllib.request.urlopen(
            "https://brandon-charles-novice-developer.github.io/march-madness-tracker/data/commentary.json"
        )
        data = json.loads(resp.read())
        assert len(data["managers"]) == 10
