#!/usr/bin/env python3
"""Unit tests for the Baseball Savant leaderboard fetch + parse helpers in
build.py and the xwOBA/xERA-aware rendering path in sections/headline.py.

Covers:
  - _parse_savant_csv: happy path, empty csv, missing player_id column,
    rows shorter than header, unicode BOM handling
  - fetch_savant_leaderboards: cache hit (no network), cache miss writes
    file, fixture mode short-circuits, network error returns empty
  - _render_hot_cold: renders xwOBA/brl% and whiff%/xERA when Savant data
    is present; re-sorts hitters by xwOBA and pitchers by xERA; falls back
    to OPS/ERA sort when Savant coverage is thin.
"""
import json
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402
from sections.headline import _render_hot_cold  # noqa: E402


BATTER_CSV = (
    '\ufeff"last_name, first_name","player_id","year","xwoba","brl_percent","whiff_percent"\n'
    '"Ohtani, Shohei",660271,2026,".423",25.6,28.9\n'
    '"Judge, Aaron",592450,2026,".410",22.1,27.3\n'
    '"Cruz, Oneil",665833,2026,".426",19.8,31.4\n'
    '"Rocchio, Brayan",677587,2026,".248",3.1,28.0\n'
    '"Story, Trevor",596115,2026,".248",,26.5\n'
)

PITCHER_CSV = (
    '\ufeff"last_name, first_name","player_id","year","xera","xwoba","whiff_percent","brl_percent"\n'
    '"Skenes, Paul",694973,2026,2.45,".251",26.4,6.7\n'
    '"Alcantara, Sandy",645261,2026,2.27,".242",27.1,5.2\n'
    '"Ober, Bailey",641927,2026,4.36,".330",19.9,\n'
)


class TestParseSavantCsv(unittest.TestCase):
    def test_happy_path_batter(self):
        parsed = build._parse_savant_csv(BATTER_CSV)
        self.assertIn("660271", parsed)
        self.assertEqual(parsed["660271"]["xwoba"], ".423")
        self.assertEqual(parsed["660271"]["brl_percent"], "25.6")
        self.assertEqual(parsed["660271"]["whiff_percent"], "28.9")

    def test_happy_path_pitcher(self):
        parsed = build._parse_savant_csv(PITCHER_CSV)
        self.assertIn("694973", parsed)
        self.assertEqual(parsed["694973"]["xera"], "2.45")
        self.assertEqual(parsed["694973"]["whiff_percent"], "26.4")

    def test_empty_values_dropped(self):
        # Story's brl_percent column is empty -> key must not appear
        parsed = build._parse_savant_csv(BATTER_CSV)
        self.assertNotIn("brl_percent", parsed["596115"])
        self.assertEqual(parsed["596115"]["xwoba"], ".248")

    def test_empty_csv(self):
        self.assertEqual(build._parse_savant_csv(""), {})

    def test_header_only(self):
        header_only = '"player_id","xwoba"\n'
        self.assertEqual(build._parse_savant_csv(header_only), {})

    def test_missing_player_id_column(self):
        bogus = '"name","xwoba"\n"Foo",".300"\n'
        self.assertEqual(build._parse_savant_csv(bogus), {})

    def test_unicode_bom_stripped(self):
        parsed = build._parse_savant_csv(BATTER_CSV)
        # If BOM wasn't stripped, "\ufefflast_name, first_name" would appear
        # as a key somewhere. Instead, all keys should be numeric pids.
        for pid in parsed:
            self.assertTrue(pid.isdigit(), f"non-numeric pid {pid!r}")


class TestFetchSavantLeaderboards(unittest.TestCase):
    def setUp(self):
        # Reset the process-level memo between tests so each case has a
        # clean slate. The on-disk cache is redirected to a temp path.
        build._SAVANT_MEM.clear()
        self._orig_cache_dir = build._SAVANT_CACHE_DIR
        build._SAVANT_CACHE_DIR = None  # force re-init under patched DATA_DIR
        self._tmp = Path(__file__).parent / "_tmp_savant_cache"
        if self._tmp.exists():
            for p in self._tmp.rglob("*"):
                if p.is_file():
                    p.unlink()
        self._patcher = mock.patch.object(build, "DATA_DIR", self._tmp)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        build._SAVANT_CACHE_DIR = self._orig_cache_dir
        build._SAVANT_MEM.clear()
        if self._tmp.exists():
            import shutil
            shutil.rmtree(self._tmp, ignore_errors=True)

    def test_fixture_mode_short_circuits(self):
        with mock.patch.object(sys, "argv", ["build.py", "--fixture", "foo.json"]):
            with mock.patch("urllib.request.urlopen") as urlopen:
                result = build.fetch_savant_leaderboards(2026, date(2026, 4, 14))
                urlopen.assert_not_called()
        self.assertEqual(result["batter"], {})
        self.assertEqual(result["pitcher"], {})
        self.assertEqual(result["schema"], 1)

    def test_happy_path_writes_cache(self):
        responses = {
            "type=batter": BATTER_CSV.encode("utf-8"),
            "type=pitcher": PITCHER_CSV.encode("utf-8"),
        }

        def fake_urlopen(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            for key, body in responses.items():
                if key in url:
                    m = mock.MagicMock()
                    m.read.return_value = body
                    m.__enter__.return_value = m
                    m.__exit__.return_value = False
                    return m
            raise AssertionError(f"unexpected url: {url}")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = build.fetch_savant_leaderboards(2026, date(2026, 4, 14))

        self.assertIn("660271", result["batter"])
        self.assertEqual(result["batter"]["660271"]["xwoba"], ".423")
        self.assertIn("694973", result["pitcher"])
        self.assertEqual(result["pitcher"]["694973"]["xera"], "2.45")

        # Cache file written
        cache_file = self._tmp / "cache" / "savant" / "leaderboards-2026-2026-04-14.json"
        self.assertTrue(cache_file.exists())
        on_disk = json.loads(cache_file.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["schema"], 1)
        self.assertIn("660271", on_disk["batter"])

    def test_cache_hit_skips_network(self):
        # Pre-populate cache file and ensure urlopen is never called.
        cache_dir = self._tmp / "cache" / "savant"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "leaderboards-2026-2026-04-14.json"
        cache_file.write_text(json.dumps({
            "schema": 1,
            "season": "2026",
            "date": "2026-04-14",
            "batter": {"111": {"xwoba": ".400"}},
            "pitcher": {"222": {"xera": "3.10"}},
        }), encoding="utf-8")

        with mock.patch("urllib.request.urlopen") as urlopen:
            result = build.fetch_savant_leaderboards(2026, date(2026, 4, 14))
            urlopen.assert_not_called()
        self.assertEqual(result["batter"]["111"]["xwoba"], ".400")
        self.assertEqual(result["pitcher"]["222"]["xera"], "3.10")

    def test_network_error_returns_empty_sides(self):
        def boom(req, timeout=None):
            raise OSError("connection refused")

        with mock.patch("urllib.request.urlopen", side_effect=boom):
            result = build.fetch_savant_leaderboards(2026, date(2026, 4, 14))
        self.assertEqual(result["batter"], {})
        self.assertEqual(result["pitcher"], {})
        self.assertEqual(result["schema"], 1)


def _roster_entry(pid, name, pos_abbr, stat):
    return {
        "person": {
            "id": pid,
            "fullName": name,
            "stats": [{"splits": [{"stat": stat}]}],
        },
        "position": {"abbreviation": pos_abbr},
    }


class TestRenderHotColdSavant(unittest.TestCase):
    def _hitters(self):
        return {"roster": [
            _roster_entry(660271, "Shohei Ohtani", "DH",
                          {"plateAppearances": 50, "avg": ".300", "homeRuns": 12, "ops": ".900"}),
            _roster_entry(592450, "Aaron Judge", "RF",
                          {"plateAppearances": 50, "avg": ".280", "homeRuns": 10, "ops": ".870"}),
            _roster_entry(665833, "Oneil Cruz", "CF",
                          {"plateAppearances": 50, "avg": ".260", "homeRuns": 8, "ops": ".820"}),
            _roster_entry(677587, "Brayan Rocchio", "SS",
                          {"plateAppearances": 50, "avg": ".210", "homeRuns": 1, "ops": ".580"}),
            _roster_entry(596115, "Trevor Story", "SS",
                          {"plateAppearances": 50, "avg": ".200", "homeRuns": 0, "ops": ".560"}),
        ]}

    def _pitchers(self):
        return {"roster": [
            _roster_entry(694973, "Paul Skenes", "P",
                          {"inningsPitched": "40.0", "era": "1.96", "strikeOuts": 55}),
            _roster_entry(645261, "Sandy Alcantara", "P",
                          {"inningsPitched": "35.0", "era": "2.10", "strikeOuts": 40}),
            _roster_entry(641927, "Bailey Ober", "P",
                          {"inningsPitched": "30.0", "era": "4.50", "strikeOuts": 25}),
        ]}

    def _savant(self):
        return {
            "batter": build._parse_savant_csv(BATTER_CSV),
            "pitcher": build._parse_savant_csv(PITCHER_CSV),
        }

    def test_renders_xwoba_and_brl_columns(self):
        html = _render_hot_cold(self._hitters(), self._pitchers(), self._savant())
        self.assertIn("xwOBA", html)
        self.assertIn("Brl", html)
        self.assertIn(".423 xwOBA", html)  # Ohtani
        self.assertIn("25.6% Brl", html)

    def test_renders_xera_and_whiff_columns(self):
        html = _render_hot_cold(self._hitters(), self._pitchers(), self._savant())
        self.assertIn("xERA", html)
        self.assertIn("Whf", html)
        self.assertIn("2.45 xERA", html)  # Skenes

    def test_sorts_hitters_by_xwoba(self):
        # Ohtani has the 2nd-highest xwOBA (.423), but Cruz has .426. So
        # Cruz should appear first in "Hitters Heating Up" even though his
        # OPS (.820) is lower than Ohtani's (.900).
        html = _render_hot_cold(self._hitters(), self._pitchers(), self._savant())
        heating = html.split("Hitters Heating Up")[1].split("Icebox")[0]
        cruz_pos = heating.find("Cruz")
        ohtani_pos = heating.find("Ohtani")
        self.assertGreater(cruz_pos, -1)
        self.assertGreater(ohtani_pos, -1)
        self.assertLess(cruz_pos, ohtani_pos, "Cruz (.426 xwOBA) should outrank Ohtani (.423)")

    def test_sorts_pitchers_by_xera(self):
        # Alcantara (2.27 xERA) should outrank Skenes (2.45 xERA) even
        # though Skenes has lower traditional ERA (1.96 vs 2.10).
        html = _render_hot_cold(self._hitters(), self._pitchers(), self._savant())
        dealing = html.split("Arms Dealing")[1].split("Doghouse")[0]
        alcantara_pos = dealing.find("Alcantara")
        skenes_pos = dealing.find("Skenes")
        self.assertGreater(alcantara_pos, -1)
        self.assertGreater(skenes_pos, -1)
        self.assertLess(alcantara_pos, skenes_pos, "Alcantara (2.27 xERA) should outrank Skenes (2.45)")

    def test_fallback_when_savant_absent(self):
        # With savant=None, the block renders without advanced columns and
        # uses the legacy OPS/ERA sort.
        html = _render_hot_cold(self._hitters(), self._pitchers(), None)
        self.assertNotIn("xwOBA", html)
        self.assertNotIn("xERA", html)
        # Ohtani (.900 OPS) should outrank everyone.
        heating = html.split("Hitters Heating Up")[1].split("Icebox")[0]
        self.assertIn("Ohtani", heating)

    def test_fallback_when_savant_coverage_is_thin(self):
        # If fewer than half the hitters have xwOBA data, the block falls
        # back to OPS sort rather than flipping the top of the list.
        thin_savant = {
            "batter": {"660271": {"xwoba": ".423"}},  # only 1 of 5 covered
            "pitcher": {},
        }
        html = _render_hot_cold(self._hitters(), self._pitchers(), thin_savant)
        # Ohtani still leads because OPS sort wins when coverage is thin.
        heating = html.split("Hitters Heating Up")[1].split("Icebox")[0]
        ohtani_pos = heating.find("Ohtani")
        cruz_pos = heating.find("Cruz")
        self.assertLess(ohtani_pos, cruz_pos)


if __name__ == "__main__":
    unittest.main(verbosity=2)
