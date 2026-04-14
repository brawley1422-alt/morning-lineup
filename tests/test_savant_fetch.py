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
from sections.scouting import _render_arsenal  # noqa: E402


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
        self.assertEqual(result["schema"], build._SAVANT_SCHEMA)

    def test_happy_path_writes_cache(self):
        def fake_urlopen(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            # Order matters — pitch-arsenal-stats URLs can also contain
            # type=batter, so check the arsenal endpoints first.
            if "pitch-arsenal-stats" in url and "type=batter" in url:
                # Distinguish current-year vs prior-year fallback fetch
                if "year=2025" in url:
                    body = ""  # prior-year empty in this test
                else:
                    body = BATTER_ARSENAL_CSV
            elif "pitch-arsenal-stats" in url:
                body = ARSENAL_STATS_CSV
            elif "pitch-arsenals" in url and "avg_speed" in url:
                body = ARSENAL_SPEED_CSV
            elif "pitch-arsenals" in url and "avg_spin" in url:
                body = ARSENAL_SPIN_CSV
            elif "type=batter" in url:
                body = BATTER_CSV
            elif "type=pitcher" in url:
                body = PITCHER_CSV
            else:
                raise AssertionError(f"unexpected url: {url}")
            m = mock.MagicMock()
            m.read.return_value = body.encode("utf-8")
            m.__enter__.return_value = m
            m.__exit__.return_value = False
            return m

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = build.fetch_savant_leaderboards(2026, date(2026, 4, 14))

        self.assertIn("660271", result["batter"])
        self.assertEqual(result["batter"]["660271"]["xwoba"], ".423")
        self.assertIn("694973", result["pitcher"])
        self.assertEqual(result["pitcher"]["694973"]["xera"], "2.45")
        # Batter arsenal also populated
        self.assertIn("batter_arsenal", result)
        self.assertIn("621020", result["batter_arsenal"])
        self.assertAlmostEqual(result["batter_arsenal"]["621020"]["SL"]["xwoba"], 0.272)

        # Cache file written
        cache_file = self._tmp / "cache" / "savant" / "leaderboards-2026-2026-04-14.json"
        self.assertTrue(cache_file.exists())
        on_disk = json.loads(cache_file.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["schema"], build._SAVANT_SCHEMA)
        self.assertIn("660271", on_disk["batter"])
        self.assertIn("batter_arsenal", on_disk)

    def test_cache_hit_skips_network(self):
        # Pre-populate cache file and ensure urlopen is never called.
        cache_dir = self._tmp / "cache" / "savant"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "leaderboards-2026-2026-04-14.json"
        cache_file.write_text(json.dumps({
            "schema": build._SAVANT_SCHEMA,
            "season": "2026",
            "date": "2026-04-14",
            "batter": {"111": {"xwoba": ".400"}},
            "pitcher": {"222": {"xera": "3.10"}},
            "arsenal": {"694973": [{"pitch": "FF", "name": "4-Seam Fastball",
                                     "usage": 50.0, "velo": 99.0, "spin": 2400,
                                     "whiff": 30.0, "xwoba_allowed": 0.250}]},
            "batter_arsenal": {"621020": {"SL": {"pa": 110, "xwoba": 0.272,
                                                  "whiff": 36.3, "hardhit": 30.0}}},
        }), encoding="utf-8")

        with mock.patch("urllib.request.urlopen") as urlopen:
            result = build.fetch_savant_leaderboards(2026, date(2026, 4, 14))
            urlopen.assert_not_called()
        self.assertEqual(result["batter"]["111"]["xwoba"], ".400")
        self.assertEqual(result["pitcher"]["222"]["xera"], "3.10")
        self.assertEqual(result["batter_arsenal"]["621020"]["SL"]["xwoba"], 0.272)

    def test_schema_bump_invalidates_old_cache(self):
        cache_dir = self._tmp / "cache" / "savant"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "leaderboards-2026-2026-04-14.json"
        # Schema 2 — missing batter_arsenal key — should be rejected
        cache_file.write_text(json.dumps({
            "schema": 2,
            "batter": {"111": {"xwoba": ".999"}},
            "pitcher": {},
            "arsenal": {},
        }), encoding="utf-8")

        calls = []
        def fake_urlopen(req, timeout=None):
            calls.append(req.full_url if hasattr(req, "full_url") else str(req))
            m = mock.MagicMock()
            m.read.return_value = b""
            m.__enter__.return_value = m
            m.__exit__.return_value = False
            return m

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = build.fetch_savant_leaderboards(2026, date(2026, 4, 14))
        self.assertTrue(len(calls) > 0, "schema mismatch should trigger refetch")
        self.assertNotIn("111", result["batter"])  # stale cache was discarded
        self.assertEqual(result["schema"], build._SAVANT_SCHEMA)

    def test_network_error_returns_empty_sides(self):
        def boom(req, timeout=None):
            raise OSError("connection refused")

        with mock.patch("urllib.request.urlopen", side_effect=boom):
            result = build.fetch_savant_leaderboards(2026, date(2026, 4, 14))
        self.assertEqual(result["batter"], {})
        self.assertEqual(result["pitcher"], {})
        self.assertEqual(result["schema"], build._SAVANT_SCHEMA)


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
        self.assertIn(".423<em>xwOBA</em>", html)  # Ohtani primary
        self.assertIn("25.6% Brl", html)            # Ohtani secondary slug

    def test_renders_xera_and_whiff_columns(self):
        html = _render_hot_cold(self._hitters(), self._pitchers(), self._savant())
        self.assertIn("xERA", html)
        self.assertIn("Whf", html)
        self.assertIn("2.45<em>xERA</em>", html)  # Skenes primary

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


ARSENAL_STATS_CSV = (
    '\ufeff"last_name, first_name","player_id","team_name_alt","pitch_type","pitch_name",'
    '"run_value_per_100","run_value","pitches","pitch_usage","pa","ba","slg","woba",'
    '"whiff_percent","k_percent","put_away","est_ba","est_slg","est_woba","hard_hit_percent"\n'
    '"Skenes, Paul",694973,"PIT","FF","4-Seam Fastball",-1.2,-8,"450",48.2,"90","0.180","0.290","0.240",30,28,20,"0.190","0.300","0.250",32\n'
    '"Skenes, Paul",694973,"PIT","SL","Slider",-0.9,-5,"240",31.7,"60","0.150","0.220","0.210",42,35,28,"0.170","0.250","0.220",25\n'
    '"Skenes, Paul",694973,"PIT","CH","Changeup",-0.5,-2,"80",10.1,"20","0.220","0.320","0.270",35,20,15,"0.230","0.330","0.280",30\n'
    '"Alcantara, Sandy",645261,"MIA","SI","Sinker",-0.3,-2,"320",42.0,"80","0.210","0.300","0.280",18,15,12,"0.220","0.310","0.290",40\n'
)

# Baseball Savant pitch-arsenal-stats?type=batter — one row per (batter, pitch_type)
BATTER_ARSENAL_CSV = (
    '\ufeff"last_name, first_name","player_id","team_name_alt","pitch_type","pitch_name",'
    '"run_value_per_100","run_value","pitches","pitch_usage","pa","ba","slg","woba",'
    '"whiff_percent","k_percent","put_away","est_ba","est_slg","est_woba","hard_hit_percent"\n'
    '"Swanson, Dansby",621020,"CHC","FF","4-Seam Fastball",1,10,"800",36.0,"192","0.260","0.440","0.370",30.4,22.0,15.0,"0.255","0.420","0.372",38.0\n'
    '"Swanson, Dansby",621020,"CHC","SL","Slider",-2,-8,"400",18.0,"110","0.190","0.290","0.270",36.3,28.0,22.0,"0.185","0.280","0.272",25.0\n'
    '"Swanson, Dansby",621020,"CHC","CH","Changeup",0,0,"180",8.0,"65","0.210","0.320","0.280",33.3,24.0,18.0,"0.205","0.310","0.283",28.0\n'
    '"Happ, Ian",664023,"CHC","FF","4-Seam Fastball",0,2,"700",34.0,"170","0.245","0.415","0.345",26.1,20.0,13.0,"0.248","0.405","0.348",35.0\n'
    '"Happ, Ian",664023,"CHC","SL","Slider",1,4,"350",17.0,"95","0.270","0.400","0.340",29.0,22.0,17.0,"0.268","0.395","0.338",32.0\n'
)

ARSENAL_SPEED_CSV = (
    '\ufeff"last_name, first_name","pitcher","ff_avg_speed","si_avg_speed","fc_avg_speed",'
    '"sl_avg_speed","ch_avg_speed","cu_avg_speed","fs_avg_speed","kn_avg_speed",'
    '"st_avg_speed","sv_avg_speed"\n'
    '"Skenes, Paul","694973","99.1",,,"88.4","89.0",,,,,\n'
    '"Alcantara, Sandy","645261",,"97.2",,,,,,,,\n'
)

ARSENAL_SPIN_CSV = (
    '\ufeff"last_name, first_name","pitcher","ff_avg_spin","si_avg_spin","fc_avg_spin",'
    '"sl_avg_spin","ch_avg_spin","cu_avg_spin","fs_avg_spin","kn_avg_spin",'
    '"st_avg_spin","sv_avg_spin"\n'
    '"Skenes, Paul","694973","2410",,,"2610","1820",,,,,\n'
    '"Alcantara, Sandy","645261",,"2180",,,,,,,,\n'
)


class TestBuildSavantArsenal(unittest.TestCase):
    def test_merges_stats_speed_spin(self):
        out = build._build_savant_arsenal(ARSENAL_STATS_CSV, ARSENAL_SPEED_CSV, ARSENAL_SPIN_CSV)
        self.assertIn("694973", out)
        skenes = out["694973"]
        self.assertEqual(len(skenes), 3)
        # Sorted by usage desc
        self.assertEqual([p["pitch"] for p in skenes], ["FF", "SL", "CH"])
        # FF has velo+spin, SL has velo+spin, CH has no velo in this fixture
        ff = skenes[0]
        self.assertEqual(ff["name"], "4-Seam Fastball")
        self.assertAlmostEqual(ff["usage"], 48.2)
        self.assertAlmostEqual(ff["velo"], 99.1)
        self.assertAlmostEqual(ff["spin"], 2410.0)
        self.assertAlmostEqual(ff["whiff"], 30.0)
        # Unit 2: xwOBA-allowed threaded from est_woba column
        self.assertAlmostEqual(ff["xwoba_allowed"], 0.250)
        sl = skenes[1]
        self.assertAlmostEqual(sl["velo"], 88.4)
        self.assertAlmostEqual(sl["xwoba_allowed"], 0.220)
        ch = skenes[2]
        self.assertAlmostEqual(ch["velo"], 89.0)
        self.assertAlmostEqual(ch["spin"], 1820.0)
        self.assertAlmostEqual(ch["xwoba_allowed"], 0.280)

    def test_handles_missing_speed_csv(self):
        out = build._build_savant_arsenal(ARSENAL_STATS_CSV, "", "")
        self.assertIn("694973", out)
        for p in out["694973"]:
            self.assertIsNone(p["velo"])
            self.assertIsNone(p["spin"])
        # Stats columns still populated
        self.assertAlmostEqual(out["694973"][0]["usage"], 48.2)

    def test_handles_missing_stats_csv(self):
        # No stats means no skeleton — result is empty even if velo/spin exist
        out = build._build_savant_arsenal("", ARSENAL_SPEED_CSV, ARSENAL_SPIN_CSV)
        self.assertEqual(out, {})

    def test_empty_returns_empty(self):
        self.assertEqual(build._build_savant_arsenal("", "", ""), {})


class TestParseBatterArsenal(unittest.TestCase):
    def test_happy_path_multi_pitch(self):
        out = build._parse_batter_arsenal(BATTER_ARSENAL_CSV)
        self.assertIn("621020", out)
        swanson = out["621020"]
        self.assertEqual(set(swanson.keys()), {"FF", "SL", "CH"})
        self.assertAlmostEqual(swanson["FF"]["xwoba"], 0.372)
        self.assertAlmostEqual(swanson["FF"]["pa"], 192.0)
        self.assertAlmostEqual(swanson["FF"]["whiff"], 30.4)
        self.assertAlmostEqual(swanson["FF"]["hardhit"], 38.0)
        self.assertAlmostEqual(swanson["SL"]["xwoba"], 0.272)
        self.assertAlmostEqual(swanson["SL"]["whiff"], 36.3)

    def test_multiple_batters(self):
        out = build._parse_batter_arsenal(BATTER_ARSENAL_CSV)
        self.assertIn("621020", out)
        self.assertIn("664023", out)
        # Happ has 2 pitches in the fixture
        self.assertEqual(set(out["664023"].keys()), {"FF", "SL"})

    def test_empty_csv(self):
        self.assertEqual(build._parse_batter_arsenal(""), {})

    def test_header_only(self):
        header_only = '"player_id","pitch_type","pa","est_woba","whiff_percent","hard_hit_percent"\n'
        self.assertEqual(build._parse_batter_arsenal(header_only), {})

    def test_missing_required_column(self):
        bogus = '"player_id","pitch_type","pa"\n"123","FF","50"\n'
        self.assertEqual(build._parse_batter_arsenal(bogus), {})

    def test_bom_stripped(self):
        out = build._parse_batter_arsenal(BATTER_ARSENAL_CSV)
        for pid in out:
            self.assertTrue(pid.isdigit(), f"non-numeric pid {pid!r}")

    def test_merge_current_over_prior(self):
        current = {"1": {"FF": {"pa": 100, "xwoba": 0.400, "whiff": 20.0, "hardhit": 35.0}}}
        prior = {
            "1": {
                "FF": {"pa": 250, "xwoba": 0.350, "whiff": 22.0, "hardhit": 33.0},
                "SL": {"pa": 180, "xwoba": 0.280, "whiff": 30.0, "hardhit": 25.0},
            },
            "2": {"FF": {"pa": 200, "xwoba": 0.330, "whiff": 24.0, "hardhit": 32.0}},
        }
        merged = build._merge_batter_arsenal(current, prior)
        # Batter 1's FF comes from current (preferred)
        self.assertAlmostEqual(merged["1"]["FF"]["xwoba"], 0.400)
        # Batter 1's SL only exists in prior — should be present
        self.assertAlmostEqual(merged["1"]["SL"]["xwoba"], 0.280)
        # Batter 2 only in prior — should be present
        self.assertAlmostEqual(merged["2"]["FF"]["xwoba"], 0.330)

    def test_merge_both_empty(self):
        self.assertEqual(build._merge_batter_arsenal({}, {}), {})

    def test_merge_only_prior(self):
        prior = {"1": {"FF": {"pa": 100, "xwoba": 0.350, "whiff": 22.0, "hardhit": 33.0}}}
        merged = build._merge_batter_arsenal({}, prior)
        self.assertAlmostEqual(merged["1"]["FF"]["xwoba"], 0.350)

    def test_empty_est_woba_becomes_none(self):
        csv_with_gap = (
            '"player_id","pitch_type","pa","est_woba","whiff_percent","hard_hit_percent"\n'
            '"999","FF","50",,25.0,30.0\n'
        )
        out = build._parse_batter_arsenal(csv_with_gap)
        self.assertIn("999", out)
        self.assertIsNone(out["999"]["FF"]["xwoba"])
        self.assertAlmostEqual(out["999"]["FF"]["whiff"], 25.0)


class TestRenderArsenal(unittest.TestCase):
    def _skenes_pitches(self):
        out = build._build_savant_arsenal(ARSENAL_STATS_CSV, ARSENAL_SPEED_CSV, ARSENAL_SPIN_CSV)
        return out["694973"]

    def test_renders_table_with_top_pitches(self):
        html = _render_arsenal(self._skenes_pitches())
        self.assertIn("sp-arsenal", html)
        self.assertIn("4-Seam Fastball", html)
        self.assertIn("Slider", html)
        self.assertIn("48%", html)  # Skenes FF usage
        self.assertIn("99.1", html)  # FF velo
        self.assertIn("2410", html)  # FF spin

    def test_caps_at_four_pitches(self):
        many = [
            {"pitch": f"P{i}", "name": f"Pitch{i}", "usage": 30 - i, "velo": 90.0, "spin": 2000, "whiff": 25}
            for i in range(6)
        ]
        html = _render_arsenal(many)
        # Only top 4 by usage should render
        self.assertIn("Pitch0", html)
        self.assertIn("Pitch3", html)
        self.assertNotIn("Pitch4", html)
        self.assertNotIn("Pitch5", html)

    def test_empty_arsenal_returns_empty_string(self):
        self.assertEqual(_render_arsenal([]), "")
        self.assertEqual(_render_arsenal(None), "")

    def test_missing_velo_spin_renders_dash(self):
        pitches = [{"pitch": "FF", "name": "4-Seam Fastball", "usage": 50.0,
                    "velo": None, "spin": None, "whiff": 25.0}]
        html = _render_arsenal(pitches)
        self.assertIn("&mdash;", html)
        self.assertIn("50%", html)
        self.assertIn("25%", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
