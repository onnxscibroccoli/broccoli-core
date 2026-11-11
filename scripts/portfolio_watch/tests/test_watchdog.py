"""Bounded, offline portfolio-watch regression tests (no GitHub network required)."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.portfolio_watch import watchdog as watch


def sample():
    return {
        "master": {"number": 102, "state": "open", "updated_at": "2026-11-11T12:00:00Z"},
        "states": {
            r: {
                "prs": [{
                    "number": 1, "state": "open", "draft": True
                }],
                "runs": [{
                    "name": "ci", "status": "completed",
                    "conclusion": "success", "head_branch": "main",
                    "head_sha": "a" * 40,
                    "html_url": f"https://github.com/{watch.OWNER}/{r}/actions/runs/1"
                }],
            } for r in watch.REPOS
        },
    }


class CampaignWatchTests(unittest.TestCase):
    def test_snapshot_allows_only_explicit_public_repos(self):
        bundle = sample()
        report = watch.evaluate(bundle["master"], bundle["states"], "2026-11-11T12:00:00Z")
        self.assertEqual(report["status"], "OBSERVED_OPEN_CAMPAIGN")
        self.assertEqual(len(report["repos"]), 7)
        self.assertTrue(all(r["draft_pr_count"] == 1 for r in report["repos"]))
        md = watch.markdown(report)
        self.assertIn("not continuous coding", md.lower())
        self.assertIn("on `main`", md)
        self.assertNotIn("lattice", md.lower())

    def test_campaign_closed_without_secondary_requests(self):
        master = {"number": 102, "state": "closed"}
        report = watch.evaluate(master, {}, "2026-11-11T12:00:00Z")
        self.assertEqual(report["status"], "CAMPAIGN_CLOSED")
        with patch.object(watch, "api_json", return_value=master) as fake:
            result = watch.observe(None, "2026-11-11T12:00:00Z")
        self.assertEqual(result["status"], "CAMPAIGN_CLOSED")
        self.assertEqual(fake.call_count, 1)

    def test_invalid_or_partial_snapshots_fail_closed(self):
        s = sample()
        del s["states"][watch.REPOS[0]]
        with self.assertRaisesRegex(ValueError, "incomplete"):
            watch.evaluate(s["master"], s["states"], "now")

    def test_truncation_is_error_not_false_count(self):
        s = sample()
        s["states"][watch.REPOS[0]]["prs"] = [
            {"number": i + 1, "state": "open"} for i in range(100)
        ]
        with self.assertRaisesRegex(ValueError, "truncated"):
            watch.evaluate(s["master"], s["states"], "now")

    def test_invalid_pr_state_or_number_rejected(self):
        s = sample()
        s["states"][watch.REPOS[1]]["prs"][0]["state"] = "closed"
        with self.assertRaisesRegex(ValueError, "unexpected PR state"):
            watch.evaluate(s["master"], s["states"], "now")
        s = sample()
        s["states"][watch.REPOS[1]]["prs"][0]["number"] = "x"
        with self.assertRaisesRegex(ValueError, "malformed PR"):
            watch.evaluate(s["master"], s["states"], "now")

    def test_wrong_master_id_rejected(self):
        s = sample()
        s["master"]["number"] = 7
        with self.assertRaisesRegex(ValueError, "master issue"):
            watch.evaluate(s["master"], s["states"], "now")

    def test_request_owner_is_allowlisted(self):
        with self.assertRaisesRegex(ValueError, "allowlisted"):
            watch.api_json("https://api.github.com/repos/another/example", None)

    def test_api_budget(self):
        s = sample()
        calls = []
        def fake(url, token):
            calls.append(url)
            if url.endswith("/issues/102"):
                return s["master"]
            if "/pulls?" in url:
                repo = url.split("/repos/")[1].split("/")[1]
                return s["states"][repo]["prs"]
            repo = url.split("/repos/")[1].split("/")[1]
            return {"workflow_runs": s["states"][repo]["runs"]}
        with patch.object(watch, "api_json", side_effect=fake):
            report = watch.observe(None, "now")
        self.assertEqual(len(calls), watch.REQUEST_BUDGET)
        self.assertEqual(report["status"], "OBSERVED_OPEN_CAMPAIGN")

if __name__ == "__main__":
    unittest.main()
