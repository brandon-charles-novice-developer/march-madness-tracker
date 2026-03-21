"""Unit tests for scoring.models — constants and configuration."""

from scoring.models import (
    API_ROUND_MAP,
    MANAGERS,
    NAME_SUFFIXES,
    PAYOUTS,
    ROUND_DATES,
    ROUND_ORDER,
)


class TestRoundOrder:
    def test_has_six_rounds(self):
        assert len(ROUND_ORDER) == 6

    def test_starts_with_r64(self):
        assert ROUND_ORDER[0] == "R64"

    def test_ends_with_championship(self):
        assert ROUND_ORDER[-1] == "Championship"

    def test_round_progression(self):
        expected = ["R64", "R32", "S16", "E8", "F4", "Championship"]
        assert ROUND_ORDER == expected


class TestRoundDates:
    def test_all_rounds_have_dates(self):
        for round_name in ROUND_ORDER:
            assert round_name in ROUND_DATES
            assert len(ROUND_DATES[round_name]) >= 1

    def test_r64_has_four_days(self):
        # 2 First Four days + 2 R64 days
        assert len(ROUND_DATES["R64"]) == 4

    def test_championship_has_one_day(self):
        assert len(ROUND_DATES["Championship"]) == 1

    def test_dates_are_iso_format(self):
        for dates in ROUND_DATES.values():
            for d in dates:
                assert len(d) == 10
                assert d[4] == "-" and d[7] == "-"


class TestAPIRoundMap:
    def test_maps_bracket_round_to_name(self):
        assert API_ROUND_MAP[2] == "R64"
        assert API_ROUND_MAP[3] == "R32"
        assert API_ROUND_MAP[7] == "Championship"

    def test_all_rounds_covered(self):
        mapped_rounds = set(API_ROUND_MAP.values())
        for r in ROUND_ORDER:
            assert r in mapped_rounds


class TestManagers:
    def test_has_ten_managers(self):
        assert len(MANAGERS) == 10

    def test_brandon_is_in_pool(self):
        assert "Brandon Nye" in MANAGERS

    def test_no_duplicates(self):
        assert len(MANAGERS) == len(set(MANAGERS))


class TestPayouts:
    def test_first_place_payout(self):
        assert PAYOUTS["first"] == 450

    def test_total_payout_matches_buyins(self):
        total_buyins = PAYOUTS["buy_in"] * 10
        total_payouts = PAYOUTS["first"] + PAYOUTS["second"]
        assert total_payouts == total_buyins


class TestNameSuffixes:
    def test_includes_jr(self):
        assert "jr" in NAME_SUFFIXES

    def test_includes_iii(self):
        assert "iii" in NAME_SUFFIXES
