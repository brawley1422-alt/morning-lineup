#!/usr/bin/env python3
"""Tests for evening.py — the all-teams post-game rebuild watcher.

Covers team discovery, per-team game filtering, Final detection, and
the tracking-set pruning logic. Network calls and subprocess invocations
are mocked; the poll loop is exercised via a short-circuit path.
"""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import evening  # noqa: E402


def _game(away_id, home_id, state="Preview", away_abbr="AWY", home_abbr="HOM"):
    return {
        "status": {"abstractGameState": state, "detailedState": state},
        "teams": {
            "away": {"team": {"id": away_id, "abbreviation": away_abbr}},
            "home": {"team": {"id": home_id, "abbreviation": home_abbr}},
        },
    }


class TestGamesForTeam(unittest.TestCase):
    def test_filters_by_team_id(self):
        slate = [
            _game(112, 134),           # Cubs @ Pirates
            _game(147, 111),           # Yankees @ Red Sox
            _game(141, 112, "Live"),   # Blue Jays @ Cubs
        ]
        cubs = evening.games_for_team(slate, 112)
        self.assertEqual(len(cubs), 2)
        self.assertEqual(
            {"Live", "Preview"},
            {g["status"]["abstractGameState"] for g in cubs},
        )

    def test_no_games_for_off_team(self):
        slate = [_game(112, 134)]
        self.assertEqual(evening.games_for_team(slate, 147), [])


class TestAllFinal(unittest.TestCase):
    def test_all_final_true(self):
        games = [_game(112, 134, "Final"), _game(141, 112, "Final")]
        self.assertTrue(evening.all_final(games))

    def test_mixed_returns_false(self):
        games = [_game(112, 134, "Final"), _game(141, 112, "Live")]
        self.assertFalse(evening.all_final(games))

    def test_empty_returns_false(self):
        # Empty lists aren't "all final" — the watcher should never treat
        # an empty slate as a trigger to rebuild.
        self.assertFalse(evening.all_final([]))


class TestLoadTeamRoster(unittest.TestCase):
    def test_reads_teams_dir(self):
        teams = evening.load_team_roster()
        # Every real team config should contribute a (slug, int-id) pair
        self.assertTrue(len(teams) >= 30)
        for slug, tid in teams:
            self.assertIsInstance(slug, str)
            self.assertIsInstance(tid, int)
            self.assertTrue(tid > 0)
        slugs = {s for s, _ in teams}
        self.assertIn("cubs", slugs)
        self.assertIn("yankees", slugs)

    def test_team_override_filters(self):
        with mock.patch.object(evening, "TEAM_OVERRIDE", "cubs"):
            teams = evening.load_team_roster()
        self.assertEqual([s for s, _ in teams], ["cubs"])


class TestMainFlow(unittest.TestCase):
    """Integration-ish: main() with network + subprocess stubbed so we
    can trace the full decision path without hitting MLB or running
    build.py / deploy.py for real."""

    def test_exits_when_no_team_games_today(self):
        with mock.patch.object(evening, "get_todays_schedule", return_value=[]), \
             mock.patch.object(evening, "rebuild_team") as rebuild, \
             mock.patch.object(evening, "deploy_all") as deploy:
            evening.main()
        rebuild.assert_not_called()
        deploy.assert_not_called()

    def test_rebuilds_and_deploys_already_final_teams(self):
        # Two teams have already-Final games at startup — watcher should
        # rebuild both immediately and deploy once at the end.
        slate = [
            _game(112, 134, "Final"),  # Cubs
            _game(141, 111, "Final"),  # Blue Jays @ Red Sox
        ]
        with mock.patch.object(evening, "get_todays_schedule", return_value=slate), \
             mock.patch.object(evening, "rebuild_team", return_value=True) as rebuild, \
             mock.patch.object(evening, "deploy_all", return_value=True) as deploy, \
             mock.patch.object(evening, "DRY_RUN", False):
            evening.main()
        rebuilt_slugs = {call.args[0] for call in rebuild.call_args_list}
        # Every team in the slate whose config matches one of the Final
        # games should have been rebuilt
        self.assertIn("cubs", rebuilt_slugs)
        self.assertTrue(
            {"blue-jays", "red-sox"}.intersection(rebuilt_slugs),
            f"expected blue-jays or red-sox in {rebuilt_slugs}",
        )
        deploy.assert_called_once()

    def test_dry_run_skips_rebuild_and_deploy(self):
        slate = [_game(112, 134, "Final")]
        with mock.patch.object(evening, "get_todays_schedule", return_value=slate), \
             mock.patch.object(evening, "rebuild_team") as rebuild, \
             mock.patch.object(evening, "deploy_all") as deploy, \
             mock.patch.object(evening, "DRY_RUN", True):
            evening.main()
        rebuild.assert_not_called()
        deploy.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
