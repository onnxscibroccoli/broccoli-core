"""Offline regression tests for branch inventory; no GitHub access required."""
from __future__ import annotations
from io import BytesIO
import json
from unittest import TestCase
from unittest.mock import patch
from scripts.portfolio.pr_inventory import fetch_open_prs, normalize, render_markdown

REPO = "onnxscibroccoli/broccoli-core"
SHA = "a" * 40

def pr(n: int, head: str, base: str = "main", *, same: bool = True) -> dict:
    return {
        "number": n, "title": f"Feature {n}",
        "head": {"ref": head, "sha": SHA, "repo": {"full_name": REPO if same else "other/fork"}},
        "base": {"ref": base, "sha": SHA}, "draft": True, "updated_at": "2026-11-11T00:00:00Z"
    }

class NormalizationTests(TestCase):
    def test_stacked_prs_are_hints_and_sorted(self):
        data = normalize(REPO, [pr(4, "child", "parent"), pr(3, "parent"), pr(9, "outside", "child", same=False)])
        self.assertEqual([x["number"] for x in data], [3, 4, 9])
        self.assertEqual(data[1]["possible_dependency_prs"], [3])
        self.assertEqual(data[2]["possible_dependency_prs"], [4])
        self.assertFalse(data[2]["same_repo_head"])

    def test_external_fork_cannot_create_same_repo_parent(self):
        data = normalize(REPO, [pr(2, "some-ref", same=False), pr(3, "child", "some-ref")])
        self.assertEqual(data[1]["possible_dependency_prs"], [])

    def test_empty_is_valid(self):
        self.assertEqual(normalize(REPO, []), [])
        self.assertIn("0 open PRs", render_markdown(REPO, []))

    def test_reject_duplicate_and_malformed_shas(self):
        with self.assertRaises(ValueError):
            normalize(REPO, [pr(1, "x"), pr(1, "y")])
        bad = pr(2, "x")
        bad["head"]["sha"] = "oops"
        with self.assertRaises(ValueError):
            normalize(REPO, [bad])

    def test_reject_unbounded_and_invalid_repo(self):
        with self.assertRaises(ValueError):
            normalize(REPO, [pr(n + 1, f"branch-{n}") for n in range(1001)])
        with self.assertRaises(ValueError):
            normalize("../../oops", [])

    def test_markdown_escapes_untrusted_titles(self):
        case = pr(5, "test")
        case["title"] = "a | [bad] `code`"
        table = render_markdown(REPO, normalize(REPO, [case]))
        self.assertIn("a \\| \\[bad\\]", table)

    def test_fetch_all_pages_without_truncation(self):
        pages = [[pr(i + 1, f"branch-{i}") for i in range(100)], [pr(101, "last")]]
        urls: list[str] = []
        def fake(request, timeout):
            urls.append(request.full_url)
            return BytesIO(json.dumps(pages[len(urls) - 1]).encode())
        with patch("scripts.portfolio.pr_inventory.urlopen", side_effect=fake):
            items = fetch_open_prs(REPO, None, max_pages=2)
        self.assertEqual(len(items), 101)
        self.assertIn("page=2", urls[1])

    def test_truncation_is_an_error_not_silent_success(self):
        page = [pr(i + 1, f"branch-{i}") for i in range(100)]
        with patch("scripts.portfolio.pr_inventory.urlopen", return_value=BytesIO(json.dumps(page).encode())):
            with self.assertRaisesRegex(ValueError, "pagination limit"):
                fetch_open_prs(REPO, None, max_pages=1)
