#!/usr/bin/env python3
"""Tests for deploy.verify_pages_build — the post-deploy check that polls
the GitHub Pages Builds API and exits non-zero when the latest build
errored. Silent GH Pages failures caused stale site content on 2026-04-13;
this verifier turns that class of bug into a loud signal.
"""
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import deploy  # noqa: E402


def _fake_response(payload):
    m = mock.MagicMock()
    m.read.return_value = json.dumps(payload).encode("utf-8")
    m.__enter__.return_value = m
    m.__exit__.return_value = False
    return m


class TestVerifyPagesBuild(unittest.TestCase):
    def test_built_on_first_poll_returns_zero(self):
        resp = _fake_response({
            "status": "built",
            "commit": "abc1234567",
            "url": "https://api.github.com/repos/x/y/pages/builds/1",
        })
        slept = []
        with mock.patch("urllib.request.urlopen", return_value=resp):
            rc = deploy.verify_pages_build(
                max_polls=5, poll_interval=0, sleep=slept.append
            )
        self.assertEqual(rc, 0)
        self.assertEqual(slept, [])  # no polling needed

    def test_building_then_built(self):
        responses = [
            _fake_response({"status": "building", "commit": "aaa"}),
            _fake_response({"status": "building", "commit": "aaa"}),
            _fake_response({"status": "built", "commit": "aaa"}),
        ]
        slept = []
        with mock.patch("urllib.request.urlopen", side_effect=responses):
            rc = deploy.verify_pages_build(
                max_polls=5, poll_interval=0, sleep=slept.append
            )
        self.assertEqual(rc, 0)
        self.assertEqual(len(slept), 2)  # slept between polls 1→2 and 2→3

    def test_errored_returns_two(self):
        resp = _fake_response({
            "status": "errored",
            "commit": "deadbeef",
            "url": "https://api.github.com/repos/x/y/pages/builds/9",
            "error": {"message": "Jekyll config invalid"},
        })
        slept = []
        buf = io.StringIO()
        with mock.patch("urllib.request.urlopen", return_value=resp), \
             mock.patch("sys.stdout", buf):
            rc = deploy.verify_pages_build(
                max_polls=5, poll_interval=0, sleep=slept.append
            )
        self.assertEqual(rc, 2)
        out = buf.getvalue()
        self.assertIn("deadbee", out)  # commit SHA printed
        self.assertIn("Jekyll config invalid", out)

    def test_failed_status_returns_two(self):
        # GitHub sometimes reports "failed" instead of "errored"
        resp = _fake_response({"status": "failed", "commit": "feedface"})
        slept = []
        with mock.patch("urllib.request.urlopen", return_value=resp):
            rc = deploy.verify_pages_build(
                max_polls=5, poll_interval=0, sleep=slept.append
            )
        self.assertEqual(rc, 2)

    def test_timeout_returns_zero_with_warning(self):
        # All polls return "building" — function should warn but not block
        stuck = _fake_response({"status": "building", "commit": "stuck"})
        responses = [stuck for _ in range(5)]
        slept = []
        buf = io.StringIO()
        with mock.patch("urllib.request.urlopen", side_effect=responses), \
             mock.patch("sys.stdout", buf):
            rc = deploy.verify_pages_build(
                max_polls=5, poll_interval=0, sleep=slept.append
            )
        self.assertEqual(rc, 0)
        self.assertIn("still", buf.getvalue())
        self.assertEqual(len(slept), 4)  # 5 polls, 4 sleeps between them

    def test_http_error_returns_zero_with_warning(self):
        import urllib.error
        err = urllib.error.HTTPError(
            url="https://api.github.com/...",
            code=500,
            msg="Server Error",
            hdrs=None,
            fp=None,
        )
        buf = io.StringIO()
        with mock.patch("urllib.request.urlopen", side_effect=err), \
             mock.patch("sys.stdout", buf):
            rc = deploy.verify_pages_build(
                max_polls=5, poll_interval=0, sleep=lambda _: None
            )
        # Non-blocking: API hiccups shouldn't fail the deploy
        self.assertEqual(rc, 0)
        self.assertIn("warning", buf.getvalue().lower())

    def test_network_error_returns_zero_with_warning(self):
        import urllib.error
        err = urllib.error.URLError("network unreachable")
        buf = io.StringIO()
        with mock.patch("urllib.request.urlopen", side_effect=err), \
             mock.patch("sys.stdout", buf):
            rc = deploy.verify_pages_build(
                max_polls=5, poll_interval=0, sleep=lambda _: None
            )
        self.assertEqual(rc, 0)
        self.assertIn("warning", buf.getvalue().lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
