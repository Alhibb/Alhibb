"""Offline unit tests for scripts/build_ui.py."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

from scripts import build_ui


def sample_raw_payload(
    *,
    contributions_1y: int = 199,
    dex_merged: int = 21,
    dex_open: int = 1,
    agentipy_merged: int = 15,
    agentipy_open: int = 2,
    pyhealth_merged: int = 5,
    pyhealth_open: int = 1,
    raen_merged: int = 1,
    goose_issues: int = 2,
) -> dict:
    return {
        "user": {
            "contributionsCollection": {
                "contributionCalendar": {
                    "totalContributions": contributions_1y,
                }
            }
        },
        "dexMerged": {"issueCount": dex_merged},
        "dexOpen": {"issueCount": dex_open},
        "agentipyMerged": {"issueCount": agentipy_merged},
        "agentipyOpen": {"issueCount": agentipy_open},
        "pyhealthMerged": {"issueCount": pyhealth_merged},
        "pyhealthOpen": {"issueCount": pyhealth_open},
        "raenMerged": {"issueCount": raen_merged},
        "gooseIssues": {"issueCount": goose_issues},
    }


SAMPLE_README = f"""# Header

Hand-authored intro.

{build_ui.OSS_START_MARKER}
stale oss
{build_ui.OSS_END_MARKER}

Hand-authored projects.

{build_ui.ACTIVITY_START_MARKER}
stale activity
{build_ui.ACTIVITY_END_MARKER}

Hand-authored footer.
"""


class TestBuildUI(unittest.TestCase):
    def test_featured_totals_and_status_distinctions(self) -> None:
        metrics = build_ui.normalize_and_validate(
            sample_raw_payload(),
            username="Alhibb",
            updated_at_utc="2026-11-19 11:46 UTC",
        )
        self.assertEqual(metrics.featured_merged_total, 42)
        self.assertEqual(metrics.featured_open_total, 4)
        self.assertEqual(metrics.goose_issues, 2)

        oss_md = build_ui.render_oss_markdown(metrics)
        self.assertIn("42 merged PRs", oss_md)
        self.assertIn("21 merged PRs (1 open PR under review)", oss_md)
        self.assertIn("15 merged PRs (2 open PRs)", oss_md)
        self.assertIn("5 merged PRs (1 open PR under review)", oss_md)
        self.assertIn("1 merged PR", oss_md)
        self.assertIn("2 bug reports (issues, not code PRs)", oss_md)

    def test_empty_and_malformed_data_rejected(self) -> None:
        with self.assertRaises(build_ui.ValidationError):
            build_ui.normalize_and_validate({})

        bad_negative = sample_raw_payload(dex_merged=-1)
        with self.assertRaises(build_ui.ValidationError):
            build_ui.normalize_and_validate(bad_negative)

        bad_bool = sample_raw_payload()
        bad_bool["raenMerged"]["issueCount"] = True
        with self.assertRaises(build_ui.ValidationError):
            build_ui.normalize_and_validate(bad_bool)

        missing_key = sample_raw_payload()
        del missing_key["gooseIssues"]
        with self.assertRaises(build_ui.ValidationError):
            build_ui.normalize_and_validate(missing_key)

    def test_svg_escaping_special_characters(self) -> None:
        svg = build_ui.render_hero_svg(
            "dark",
            name='Ibrahim & <Rabiu> "Dev"',
            username="Alhibb's",
            headline="AI & ML <Systems>",
            supporting_line="Agents & Tooling",
            org_line="DevClans & Co",
        )
        root = ET.fromstring(svg)
        self.assertTrue(root.tag.endswith("svg"))
        self.assertIn("Ibrahim &amp; &lt;Rabiu&gt; &quot;Dev&quot;", svg)
        self.assertIn("@Alhibb&#x27;s", svg)

    def test_dark_and_light_theme_factual_parity(self) -> None:
        metrics = build_ui.normalize_and_validate(
            sample_raw_payload(),
            username="Alhibb",
            updated_at_utc="2026-11-19 11:46 UTC",
        )
        dark_svg = build_ui.render_summary_svg(metrics, "dark")
        light_svg = build_ui.render_summary_svg(metrics, "light")

        dark_texts = [el.text for el in ET.fromstring(dark_svg).iter() if el.text and el.text.strip()]
        light_texts = [el.text for el in ET.fromstring(light_svg).iter() if el.text and el.text.strip()]
        self.assertEqual(dark_texts, light_texts)
        self.assertIn("42 merged", dark_texts)
        self.assertIn("199", dark_texts)
        self.assertIn("2 filed", dark_texts)

    def test_marked_sections_preserve_surrounding_content_and_are_deterministic(self) -> None:
        metrics = build_ui.normalize_and_validate(
            sample_raw_payload(),
            username="Alhibb",
            updated_at_utc="2026-11-19 11:46 UTC",
        )
        svgs_a, readme_a = build_ui.generate_outputs(metrics, SAMPLE_README)
        svgs_b, readme_b = build_ui.generate_outputs(metrics, SAMPLE_README)

        self.assertEqual(svgs_a, svgs_b)
        self.assertEqual(readme_a, readme_b)
        self.assertIn("Hand-authored intro.", readme_a)
        self.assertIn("Hand-authored projects.", readme_a)
        self.assertIn("Hand-authored footer.", readme_a)
        self.assertNotIn("stale oss", readme_a)
        self.assertNotIn("stale activity", readme_a)

    def test_failure_preserves_last_good_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            assets = base / "assets"
            assets.mkdir()
            sentinel_svg = "<svg xmlns='http://www.w3.org/2000/svg'><text>last-good</text></svg>"
            (assets / "hero-dark.svg").write_text(sentinel_svg, encoding="utf-8")
            (base / "README.md").write_text(SAMPLE_README, encoding="utf-8")

            bad_fixture = base / "bad.json"
            bad_fixture.write_text(json.dumps({"user": None}), encoding="utf-8")

            with self.assertRaises(build_ui.ValidationError):
                build_ui.main(["--base-dir", str(base), "--input-json", str(bad_fixture)])

            self.assertEqual((assets / "hero-dark.svg").read_text(encoding="utf-8"), sentinel_svg)
            self.assertEqual((base / "README.md").read_text(encoding="utf-8"), SAMPLE_README)

    def test_rate_limit_fails_immediately_without_retries(self) -> None:
        err = urllib.error.HTTPError(
            url="https://api.github.com/graphql",
            code=403,
            msg="Forbidden",
            hdrs={"X-RateLimit-Remaining": "0"},
            fp=io.BytesIO(b"{}"),
        )
        with mock.patch("urllib.request.urlopen", side_effect=err) as mock_open:
            with self.assertRaises(build_ui.GitHubAPIError):
                build_ui.fetch_github_data("Alhibb", "fake-token", max_retries=2)
            self.assertEqual(mock_open.call_count, 1)


if __name__ == "__main__":
    unittest.main()
