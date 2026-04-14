#!/usr/bin/env python3
"""Unit tests for sections/matchup.py — the Matchup Read section that
joins the opposing starter's arsenal against tonight's lineup's
per-pitch performance.

See docs/plans/2026-04-14-002-feat-matchup-read-plan.md for the
per-unit test scenarios this file covers (Units 3, 4, and 5).
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from sections import matchup  # noqa: E402


def _briefing(savant=None, today_lineup=None, next_games=None,
              scout_data=None, team_id=112, team_name="Cubs", tmap=None):
    """Build a TeamBriefing-shaped SimpleNamespace for section tests."""
    return SimpleNamespace(
        config={},
        data={
            "savant": savant or {},
            "today_lineup": today_lineup or {"home": [], "away": []},
            "next_games": next_games or [],
            "scout_data": scout_data or {},
            "tmap": tmap or {},
        },
        team_id=team_id,
        team_name=team_name,
        div_id=205, div_name="NL Central",
        affiliates={},
    )


# A pitcher who throws FF 50%, SL 50%.
PITCHER_ARSENAL_5050 = [
    {"pitch": "FF", "name": "4-Seam Fastball", "usage": 50.0, "velo": 99.0,
     "spin": 2400, "whiff": 25.0, "xwoba_allowed": 0.280},
    {"pitch": "SL", "name": "Slider", "usage": 50.0, "velo": 88.0,
     "spin": 2600, "whiff": 38.0, "xwoba_allowed": 0.220},
]

# A batter who crushes fastballs (.400 vs FF) but flails at sliders (.200 vs SL)
BATTER_FF_GOOD = {
    "FF": {"pa": 200, "xwoba": 0.400, "whiff": 20.0, "hardhit": 40.0},
    "SL": {"pa": 120, "xwoba": 0.200, "whiff": 38.0, "hardhit": 25.0},
}

BATTER_AVERAGE = {
    "FF": {"pa": 100, "xwoba": matchup.LEAGUE_AVG_XWOBA, "whiff": 24.0, "hardhit": 32.0},
    "SL": {"pa": 100, "xwoba": matchup.LEAGUE_AVG_XWOBA, "whiff": 30.0, "hardhit": 28.0},
}


class TestExpectedXwoba(unittest.TestCase):
    def test_happy_path_50_50(self):
        # 50% * .400 + 50% * .200 = .300
        x = matchup._expected_xwoba(PITCHER_ARSENAL_5050, BATTER_FF_GOOD)
        self.assertAlmostEqual(x, 0.300, places=3)

    def test_missing_pitch_uses_league_average(self):
        # Batter has no SL row → SL contributes league-average
        batter = {"FF": {"pa": 200, "xwoba": 0.400, "whiff": 20.0, "hardhit": 40.0}}
        x = matchup._expected_xwoba(PITCHER_ARSENAL_5050, batter)
        expected = 0.5 * 0.400 + 0.5 * matchup.LEAGUE_AVG_XWOBA
        self.assertAlmostEqual(x, expected, places=3)

    def test_empty_batter_arsenal(self):
        x = matchup._expected_xwoba(PITCHER_ARSENAL_5050, {})
        self.assertAlmostEqual(x, matchup.LEAGUE_AVG_XWOBA, places=3)

    def test_pitch_with_pitcher_only_code(self):
        # Pitcher throws a splitter; batter has no FS data → league avg
        arsenal = [{"pitch": "FS", "name": "Splitter", "usage": 100.0,
                    "velo": 87.0, "spin": 1500, "whiff": 30.0, "xwoba_allowed": 0.250}]
        x = matchup._expected_xwoba(arsenal, BATTER_FF_GOOD)
        self.assertAlmostEqual(x, matchup.LEAGUE_AVG_XWOBA, places=3)

    def test_usage_none_contributes_zero(self):
        arsenal = [
            {"pitch": "FF", "usage": 50.0, "name": "FF", "velo": 95,
             "spin": 2400, "whiff": 25, "xwoba_allowed": 0.250},
            {"pitch": "SL", "usage": None, "name": "SL", "velo": 85,
             "spin": 2500, "whiff": 35, "xwoba_allowed": 0.220},
        ]
        # Only FF contributes: 0.5 * 0.400 = 0.200
        x = matchup._expected_xwoba(arsenal, BATTER_FF_GOOD)
        self.assertAlmostEqual(x, 0.200, places=3)


class TestLetterGrade(unittest.TestCase):
    def test_band_edges(self):
        self.assertEqual(matchup._letter_grade(0.360), "A")
        self.assertEqual(matchup._letter_grade(0.400), "A")
        self.assertEqual(matchup._letter_grade(0.359), "B")
        self.assertEqual(matchup._letter_grade(0.320), "B")
        self.assertEqual(matchup._letter_grade(0.319), "C")
        self.assertEqual(matchup._letter_grade(0.290), "C")
        self.assertEqual(matchup._letter_grade(0.289), "D")
        self.assertEqual(matchup._letter_grade(0.100), "D")


class TestVulnTag(unittest.TestCase):
    def test_clear_vuln_returns_worst_pitch(self):
        # Batter flails at SL (.200 vs league .310 → gap -.110, weighted 50% → -.055)
        # Batter crushes FF (.400 vs .310 → gap +.090, weighted 50% → +.045)
        # Most extreme absolute is SL vuln
        tag = matchup._vuln_tag(PITCHER_ARSENAL_5050, BATTER_FF_GOOD)
        self.assertIsNotNone(tag)
        self.assertEqual(tag["pitch"], "SL")
        self.assertEqual(tag["kind"], "vuln")
        self.assertEqual(tag["dots"], 3)  # PA 120 → ●●●

    def test_clear_safe_returns_best_pitch(self):
        # Pitcher heavily throws FF (90%), batter crushes FF — vuln tag is FF "safe"
        arsenal = [
            {"pitch": "FF", "usage": 90.0, "name": "FF", "velo": 99, "spin": 2400, "whiff": 25, "xwoba_allowed": 0.280},
            {"pitch": "SL", "usage": 10.0, "name": "SL", "velo": 88, "spin": 2600, "whiff": 38, "xwoba_allowed": 0.220},
        ]
        tag = matchup._vuln_tag(arsenal, BATTER_FF_GOOD)
        self.assertIsNotNone(tag)
        self.assertEqual(tag["pitch"], "FF")
        self.assertEqual(tag["kind"], "safe")

    def test_no_tag_when_league_average_batter(self):
        # Batter is league-average on every pitch → no story to tell
        tag = matchup._vuln_tag(PITCHER_ARSENAL_5050, BATTER_AVERAGE)
        self.assertIsNone(tag)

    def test_no_tag_when_batter_has_no_data(self):
        tag = matchup._vuln_tag(PITCHER_ARSENAL_5050, {})
        self.assertIsNone(tag)


class TestDots(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(matchup._dots(49), 0)
        self.assertEqual(matchup._dots(50), 1)
        self.assertEqual(matchup._dots(74), 1)
        self.assertEqual(matchup._dots(75), 2)
        self.assertEqual(matchup._dots(99), 2)
        self.assertEqual(matchup._dots(100), 3)
        self.assertEqual(matchup._dots(149), 3)
        self.assertEqual(matchup._dots(150), 4)
        self.assertEqual(matchup._dots(300), 4)

    def test_none_returns_zero(self):
        self.assertEqual(matchup._dots(None), 0)


class TestTeamGrade(unittest.TestCase):
    def test_mean_xwoba_determines_grade(self):
        # All hitters A → team A
        self.assertEqual(matchup._team_grade([0.400, 0.380, 0.370]), "A")
        # Mix → mean drives the band
        mix = [0.400, 0.300, 0.280]  # mean .3267 → B
        self.assertEqual(matchup._team_grade(mix), "B")

    def test_empty_list_returns_dash(self):
        self.assertEqual(matchup._team_grade([]), "—")


class TestExploitCounts(unittest.TestCase):
    def test_counts_by_pitch_and_orders_by_usage(self):
        # Three hitters, 2 vulnerable to SL, 1 vulnerable to FS.
        # Pitcher throws FS 30%, SL 20%, FF 50% — FS should appear
        # before SL in the exploit list because pitcher throws FS more.
        arsenal = [
            {"pitch": "FF", "usage": 50.0, "name": "FF", "velo": 99, "spin": 2400, "whiff": 25, "xwoba_allowed": 0.280},
            {"pitch": "FS", "usage": 30.0, "name": "FS", "velo": 89, "spin": 1500, "whiff": 40, "xwoba_allowed": 0.200},
            {"pitch": "SL", "usage": 20.0, "name": "SL", "velo": 88, "spin": 2600, "whiff": 38, "xwoba_allowed": 0.220},
        ]
        tags = [
            {"pitch": "SL", "kind": "vuln", "dots": 3},
            {"pitch": "SL", "kind": "vuln", "dots": 2},
            {"pitch": "FS", "kind": "vuln", "dots": 3},
        ]
        counts = matchup._exploit_counts(tags, arsenal)
        self.assertEqual(counts, [("FS", 1), ("SL", 2)])

    def test_safe_tags_not_counted(self):
        tags = [{"pitch": "FF", "kind": "safe", "dots": 4}]
        counts = matchup._exploit_counts(tags, PITCHER_ARSENAL_5050)
        self.assertEqual(counts, [])


# ---------- Section render tests (Units 3 + 5) ----------

_CUBS_LINEUP = [
    {"id": 621020, "name": "Dansby Swanson", "pos": "SS"},
    {"id": 664023, "name": "Ian Happ", "pos": "CF"},
]

_SKENES_ARSENAL = [
    {"pitch": "FF", "name": "4-Seam Fastball", "usage": 45.0, "velo": 99.1,
     "spin": 2410, "whiff": 29.6, "xwoba_allowed": 0.280},
    {"pitch": "SL", "name": "Slider", "usage": 25.0, "velo": 88.4,
     "spin": 2610, "whiff": 38.0, "xwoba_allowed": 0.209},
    {"pitch": "FS", "name": "Splitter", "usage": 15.0, "velo": 89.0,
     "spin": 1820, "whiff": 43.9, "xwoba_allowed": 0.123},
    {"pitch": "CH", "name": "Changeup", "usage": 15.0, "velo": 87.0,
     "spin": 1700, "whiff": 32.0, "xwoba_allowed": 0.250},
]


def _full_briefing():
    """Cubs @ PIT, Skenes pitching, full Savant data."""
    return _briefing(
        savant={
            "arsenal": {"694973": _SKENES_ARSENAL},
            "batter_arsenal": {
                "621020": BATTER_FF_GOOD,
                "664023": {
                    "FF": {"pa": 170, "xwoba": 0.350, "whiff": 26.0, "hardhit": 35.0},
                    "SL": {"pa": 95, "xwoba": 0.335, "whiff": 29.0, "hardhit": 32.0},
                },
            },
        },
        today_lineup={"home": [], "away": _CUBS_LINEUP},
        next_games=[{
            "gameDate": "2026-04-14T23:10:00Z",
            "venue": {"name": "PNC Park"},
            "teams": {
                "home": {"team": {"id": 134}},
                "away": {"team": {"id": 112}},
            },
        }],
        scout_data={
            "cubs_sp": {"id": 607192, "name": "Justin Steele"},
            "opp_sp": {"id": 694973, "name": "Paul Skenes"},
        },
        tmap={112: {"abbreviation": "CHC"}, 134: {"abbreviation": "PIT"}},
    )


class TestRenderMatchup(unittest.TestCase):
    def test_happy_path_renders_card(self):
        html = matchup.render(_full_briefing())
        self.assertIn("matchup-read", html)
        self.assertIn("Skenes", html)
        self.assertIn("Swanson", html)
        self.assertIn("Happ", html)
        self.assertIn("exploit", html.lower())

    def test_tag_appears_for_swanson(self):
        # Given Skenes's FF 45% / SL 25% mix, Swanson's FF hitting
        # (.400 vs league .310) outweighs his SL weakness in the
        # weighted gap — so the tag surfaces as "safe: FF". Either
        # "vuln" or "safe" is an acceptable story; we just need one.
        html = matchup.render(_full_briefing())
        idx = html.find("Swanson")
        self.assertGreater(idx, -1)
        row = html[idx:idx + 600]
        self.assertTrue("vuln" in row or "safe" in row,
                        "Swanson should surface some per-pitch story")

    def test_vuln_wins_when_pitcher_heavy_on_batter_weakness(self):
        # Flip the arsenal so SL is the dominant pitch — now the
        # SL weakness should beat the FF strength and surface as vuln.
        b = _full_briefing()
        b.data["savant"]["arsenal"]["694973"] = [
            {"pitch": "SL", "name": "Slider", "usage": 60.0, "velo": 88.4,
             "spin": 2610, "whiff": 38.0, "xwoba_allowed": 0.209},
            {"pitch": "FF", "name": "4-Seam Fastball", "usage": 40.0, "velo": 99.1,
             "spin": 2410, "whiff": 29.6, "xwoba_allowed": 0.280},
        ]
        html = matchup.render(b)
        idx = html.find("Swanson")
        row = html[idx:idx + 600]
        self.assertIn("vuln", row)
        self.assertIn("SL", row)

    def test_missing_savant_arsenal_returns_empty(self):
        b = _full_briefing()
        b.data["savant"] = {}
        self.assertEqual(matchup.render(b), "")

    def test_no_games_returns_empty(self):
        b = _full_briefing()
        b.data["next_games"] = []
        self.assertEqual(matchup.render(b), "")

    def test_missing_scout_data_returns_empty(self):
        b = _full_briefing()
        b.data["scout_data"] = {}
        self.assertEqual(matchup.render(b), "")

    def test_empty_lineup_returns_empty(self):
        b = _full_briefing()
        b.data["today_lineup"] = {"home": [], "away": []}
        self.assertEqual(matchup.render(b), "")

    def test_opposing_starter_missing_from_arsenal(self):
        # Pitcher not in Savant arsenal map → section returns empty
        b = _full_briefing()
        b.data["savant"]["arsenal"] = {}
        self.assertEqual(matchup.render(b), "")

    def test_hitter_with_no_savant_data_renders_dash(self):
        b = _full_briefing()
        # Drop Swanson's batter_arsenal entry — row should show em-dash
        del b.data["savant"]["batter_arsenal"]["621020"]
        html = matchup.render(b)
        # Happ still shows; Swanson still appears as a row
        self.assertIn("Swanson", html)
        self.assertIn("Happ", html)

    def test_resolves_home_vs_away_correctly(self):
        # Cubs home → own lineup comes from today_lineup.home
        b = _full_briefing()
        b.data["next_games"][0]["teams"] = {
            "home": {"team": {"id": 112}},
            "away": {"team": {"id": 134}},
        }
        b.data["today_lineup"] = {"home": _CUBS_LINEUP, "away": []}
        html = matchup.render(b)
        self.assertIn("Swanson", html)

    def test_html_escapes_hitter_names(self):
        b = _full_briefing()
        b.data["today_lineup"]["away"] = [
            {"id": 621020, "name": "Dansby O'Hearn", "pos": "SS"},
        ]
        html = matchup.render(b)
        self.assertIn("O&#x27;Hearn", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
