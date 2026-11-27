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
    contributions_1y: int = 210,
    dex_merged: int = 24,
    dex_open: int = 1,
    agentipy_merged: int = 15,
    agentipy_open: int = 2,
    pyhealth_merged: int = 7,
    pyhealth_open: int = 0,
    raen_merged: int = 1,
    goose_merged: int = 1,
    goose_open: int = 1,
    goose_issues: int = 3,
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
        "gooseMerged": {"issueCount": goose_merged},
        "gooseOpen": {"issueCount": goose_open},
        "gooseIssues": {"issueCount": goose_issues},
    }


SAMPLE_README = f"""# Header

Hand-authored intro.

{build_ui.ACTIVITY_START_MARKER}
stale activity
{build_ui.ACTIVITY_END_MARKER}

Hand-authored footer.
"""


class TestBuildUI(unittest.TestCase):
    def test_featured_totals_and_card_badges(self) -> None:
        metrics = build_ui.normalize_and_validate(
            sample_raw_payload(),
            username="Alhibb",
            updated_at_utc="2026-11-27 11:46 UTC",
        )
        self.assertEqual(metrics.featured_merged_total, 48)
        self.assertEqual(metrics.featured_open_total, 4)
        self.assertEqual(metrics.goose_issues, 3)

        cards = build_ui.render_oss_cards(metrics, "dark")
        self.assertIn("1 MERGED PR", cards["oss-goose-dark.svg"])
        self.assertIn("1 OPEN PR", cards["oss-goose-dark.svg"])
        self.assertIn("3 BUG REPORTS", cards["oss-goose-dark.svg"])
        self.assertIn("24 MERGED", cards["oss-dex-dark.svg"])
        self.assertIn("15 MERGED", cards["oss-agentipy-dark.svg"])
        self.assertIn("7 MERGED", cards["oss-pyhealth-dark.svg"])
        self.assertIn("1 MERGED", cards["oss-raen-dark.svg"])

    def test_empty_and_malformed_data_rejected(self) -> None:
        with self.assertRaises(build_ui.ValidationError):
            build_ui.normalize_and_validate({})

        with self.assertRaises(build_ui.ValidationError):
            build_ui.normalize_and_validate(sample_raw_payload(goose_merged=-1))

        bad_bool = sample_raw_payload()
        bad_bool["raenMerged"]["issueCount"] = True
        with self.assertRaises(build_ui.ValidationError):
            build_ui.normalize_and_validate(bad_bool)

        missing_key = sample_raw_payload()
        del missing_key["gooseMerged"]
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
            sub_org_line="DevClans & AgentConform",
        )
        root = ET.fromstring(svg)
        self.assertTrue(root.tag.endswith("svg"))
        self.assertIn("Ibrahim &amp; &lt;Rabiu&gt; &quot;Dev&quot;", svg)
        self.assertIn("@Alhibb&#x27;s", svg)

    def test_dark_and_light_theme_factual_parity_across_all_cards(self) -> None:
        metrics = build_ui.normalize_and_validate(
            sample_raw_payload(),
            username="Alhibb",
            updated_at_utc="2026-11-27 11:46 UTC",
        )
        svgs, _ = build_ui.generate_outputs(metrics, SAMPLE_README)
        self.assertEqual(len(svgs), 26)

        dark_names = sorted(k for k in svgs if k.endswith("-dark.svg"))
        for dark_name in dark_names:
            light_name = dark_name.replace("-dark.svg", "-light.svg")
            self.assertIn(light_name, svgs)
            dark_texts = [el.text.strip() for el in ET.fromstring(svgs[dark_name]).iter() if el.text and el.text.strip()]
            light_texts = [el.text.strip() for el in ET.fromstring(svgs[light_name]).iter() if el.text and el.text.strip()]
            self.assertEqual(dark_texts, light_texts, f"Parity mismatch for {dark_name}")

    def test_skip_if_unchanged_prevents_timestamp_only_rewrites(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "README.md").write_text(SAMPLE_README, encoding="utf-8")
            fixture = base / "data.json"
            fixture.write_text(json.dumps(sample_raw_payload()), encoding="utf-8")

            build_ui.main(["--base-dir", str(base), "--input-json", str(fixture), "--timestamp", "2026-11-27 10:00 UTC"])
            first_readme = (base / "README.md").read_text(encoding="utf-8")
            self.assertIn("2026-11-27 10:00 UTC", first_readme)

            # Second run with identical metrics and --skip-if-unchanged should not bump timestamp
            build_ui.main([
                "--base-dir", str(base),
                "--input-json", str(fixture),
                "--timestamp", "2026-11-27 16:00 UTC",
                "--skip-if-unchanged",
            ])
            second_readme = (base / "README.md").read_text(encoding="utf-8")
            self.assertEqual(first_readme, second_readme)

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
