"""Generate theme-adaptive SVG assets and refresh marked Markdown sections for Alhibb's GitHub profile."""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROFILE_USERNAME = os.environ.get("PROFILE_USERNAME", "Alhibb").strip() or "Alhibb"
DISPLAY_NAME = "Ibrahim Rabiu"
HEADLINE = "AI & Software Engineer"
SUPPORTING_LINE = "AI Agents · Applied ML · Developer Tooling"
ORG_LINE = "DEVCLANS SOLUTION LTD · NIGERIA"

OSS_START_MARKER = "<!-- OSS_IMPACT:START -->"
OSS_END_MARKER = "<!-- OSS_IMPACT:END -->"
ACTIVITY_START_MARKER = "<!-- ACTIVITY_SUMMARY:START -->"
ACTIVITY_END_MARKER = "<!-- ACTIVITY_SUMMARY:END -->"

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#09090B",
        "card": "#111114",
        "card_inner": "#18181B",
        "border": "#27272A",
        "dot": "#27272A",
        "text": "#FAFAFA",
        "sub": "#D4D4D8",
        "muted": "#A1A1AA",
        "accent": "#22D3EE",
        "accent2": "#A855F7",
        "glow_opacity": "0.16",
    },
    "light": {
        "bg": "#FFFFFF",
        "card": "#FAFAFA",
        "card_inner": "#F4F4F5",
        "border": "#E4E4E7",
        "dot": "#D4D4D8",
        "text": "#09090B",
        "sub": "#3F3F46",
        "muted": "#52525B",
        "accent": "#0284C7",
        "accent2": "#7C3AED",
        "glow_opacity": "0.10",
    },
}

GRAPHQL_QUERY = """
query($login: String!, $qDexMerged: String!, $qDexOpen: String!, $qAgentipyMerged: String!, $qAgentipyOpen: String!, $qPyhealthMerged: String!, $qPyhealthOpen: String!, $qRaenMerged: String!, $qGooseIssues: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
      }
    }
  }
  dexMerged: search(query: $qDexMerged, type: ISSUE, first: 1) {
    issueCount
  }
  dexOpen: search(query: $qDexOpen, type: ISSUE, first: 1) {
    issueCount
  }
  agentipyMerged: search(query: $qAgentipyMerged, type: ISSUE, first: 1) {
    issueCount
  }
  agentipyOpen: search(query: $qAgentipyOpen, type: ISSUE, first: 1) {
    issueCount
  }
  pyhealthMerged: search(query: $qPyhealthMerged, type: ISSUE, first: 1) {
    issueCount
  }
  pyhealthOpen: search(query: $qPyhealthOpen, type: ISSUE, first: 1) {
    issueCount
  }
  raenMerged: search(query: $qRaenMerged, type: ISSUE, first: 1) {
    issueCount
  }
  gooseIssues: search(query: $qGooseIssues, type: ISSUE, first: 1) {
    issueCount
  }
}
"""


class GitHubAPIError(RuntimeError):
    """Raised when GitHub API retrieval fails."""


class ValidationError(ValueError):
    """Raised when fetched data or generated output fails validation."""


@dataclass(frozen=True)
class ProfileMetrics:
    username: str
    contributions_1y: int
    dex_merged: int
    dex_open: int
    agentipy_merged: int
    agentipy_open: int
    pyhealth_merged: int
    pyhealth_open: int
    raen_merged: int
    goose_issues: int
    updated_at_utc: str

    @property
    def featured_merged_total(self) -> int:
        return (
            self.dex_merged
            + self.agentipy_merged
            + self.pyhealth_merged
            + self.raen_merged
        )

    @property
    def featured_open_total(self) -> int:
        return self.dex_open + self.agentipy_open + self.pyhealth_open


def build_query_variables(username: str) -> dict[str, str]:
    return {
        "login": username,
        "qDexMerged": f"repo:exmergo/dex is:pr author:{username} is:merged",
        "qDexOpen": f"repo:exmergo/dex is:pr author:{username} is:open",
        "qAgentipyMerged": f"repo:niceberginc/agentipy is:pr author:{username} is:merged",
        "qAgentipyOpen": f"repo:niceberginc/agentipy is:pr author:{username} is:open",
        "qPyhealthMerged": f"repo:sunlabuiuc/PyHealth is:pr author:{username} is:merged",
        "qPyhealthOpen": f"repo:sunlabuiuc/PyHealth is:pr author:{username} is:open",
        "qRaenMerged": f"repo:bshelby88/raen-bounties is:pr author:{username} is:merged",
        "qGooseIssues": f"repo:aaif-goose/goose is:issue author:{username}",
    }


def fetch_github_data(
    username: str,
    token: str,
    *,
    timeout: int = 20,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Fetch public GitHub GraphQL metrics with bounded transient retry and rate-limit awareness."""
    if not token:
        raise GitHubAPIError("GITHUB_TOKEN is required for live GitHub GraphQL requests.")

    payload = json.dumps(
        {"query": GRAPHQL_QUERY, "variables": build_query_variables(username)}
    ).encode("utf-8")

    headers = {
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": f"{username}-profile-generator",
    }

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=payload,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
            parsed = json.loads(body)
            if not isinstance(parsed, dict):
                raise GitHubAPIError("Unexpected non-object GraphQL response.")
            if parsed.get("errors"):
                raise GitHubAPIError(f"GraphQL returned errors: {parsed['errors']}")
            data = parsed.get("data")
            if not isinstance(data, dict):
                raise GitHubAPIError("GraphQL response missing 'data' object.")
            return data
        except urllib.error.HTTPError as exc:
            # Respect rate limits and client errors immediately; do not retry indefinitely.
            remaining = exc.headers.get("X-RateLimit-Remaining") if exc.headers else None
            if exc.code in (401, 403, 429) or remaining == "0":
                raise GitHubAPIError(
                    f"GitHub API request rejected (HTTP {exc.code}, rate-limit remaining={remaining})."
                ) from exc
            if 500 <= exc.code < 600 and attempt < max_retries:
                last_error = exc
                time.sleep(2 ** attempt)
                continue
            raise GitHubAPIError(f"GitHub API HTTP error {exc.code}: {exc.reason}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            raise GitHubAPIError(f"GitHub API request failed after retries: {exc}") from exc

    raise GitHubAPIError(f"GitHub API request failed: {last_error}")


def _require_non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(f"Expected non-negative integer for '{field_name}', got {value!r}.")
    return value


def _extract_issue_count(raw_data: dict[str, Any], key: str) -> int:
    node = raw_data.get(key)
    if not isinstance(node, dict) or "issueCount" not in node:
        raise ValidationError(f"Missing required search count '{key}.issueCount'.")
    return _require_non_negative_int(node["issueCount"], f"{key}.issueCount")


def normalize_and_validate(
    raw_data: dict[str, Any],
    *,
    username: str = PROFILE_USERNAME,
    updated_at_utc: str | None = None,
) -> ProfileMetrics:
    """Validate GraphQL payload and return normalized ProfileMetrics."""
    if not isinstance(raw_data, dict):
        raise ValidationError("Raw GitHub data must be a dictionary.")

    user = raw_data.get("user")
    if not isinstance(user, dict):
        raise ValidationError("Missing 'user' object in GitHub response.")

    contrib_collection = user.get("contributionsCollection")
    if not isinstance(contrib_collection, dict):
        raise ValidationError("Missing 'user.contributionsCollection'.")

    calendar = contrib_collection.get("contributionCalendar")
    if not isinstance(calendar, dict) or "totalContributions" not in calendar:
        raise ValidationError("Missing 'user.contributionsCollection.contributionCalendar.totalContributions'.")

    contributions_1y = _require_non_negative_int(
        calendar["totalContributions"], "totalContributions"
    )

    timestamp = updated_at_utc or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if not isinstance(timestamp, str) or not timestamp.strip():
        raise ValidationError("updated_at_utc must be a non-empty string.")

    return ProfileMetrics(
        username=username,
        contributions_1y=contributions_1y,
        dex_merged=_extract_issue_count(raw_data, "dexMerged"),
        dex_open=_extract_issue_count(raw_data, "dexOpen"),
        agentipy_merged=_extract_issue_count(raw_data, "agentipyMerged"),
        agentipy_open=_extract_issue_count(raw_data, "agentipyOpen"),
        pyhealth_merged=_extract_issue_count(raw_data, "pyhealthMerged"),
        pyhealth_open=_extract_issue_count(raw_data, "pyhealthOpen"),
        raen_merged=_extract_issue_count(raw_data, "raenMerged"),
        goose_issues=_extract_issue_count(raw_data, "gooseIssues"),
        updated_at_utc=timestamp.strip(),
    )


def esc(text: Any) -> str:
    """Escape text safely for XML/SVG interpolation."""
    return html.escape(str(text if text is not None else ""), quote=True)


def fmt_count(n: int) -> str:
    return f"{n:,}"


def pluralize(count: int, singular: str, plural: str | None = None) -> str:
    word = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {word}"


def render_hero_svg(
    theme_name: str,
    *,
    name: str = DISPLAY_NAME,
    username: str = PROFILE_USERNAME,
    headline: str = HEADLINE,
    supporting_line: str = SUPPORTING_LINE,
    org_line: str = ORG_LINE,
) -> str:
    """Render a clean, high-contrast, mobile-legible Hero SVG."""
    if theme_name not in THEMES:
        raise ValidationError(f"Unsupported theme: {theme_name}")
    t = THEMES[theme_name]

    return f'''<svg width="840" height="196" viewBox="0 0 840 196" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{esc(name)} (@{esc(username)}) — {esc(headline)}">
  <defs>
    <pattern id="dots-{theme_name}" width="20" height="20" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="0.9" fill="{t["dot"]}" opacity="0.65"/>
    </pattern>
    <radialGradient id="glow1-{theme_name}" cx="88%" cy="18%" r="55%">
      <stop offset="0%" stop-color="{t["accent"]}" stop-opacity="{t["glow_opacity"]}"/>
      <stop offset="100%" stop-color="{t["bg"]}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glow2-{theme_name}" cx="14%" cy="5%" r="48%">
      <stop offset="0%" stop-color="{t["accent2"]}" stop-opacity="{t["glow_opacity"]}"/>
      <stop offset="100%" stop-color="{t["bg"]}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="accent-bar-{theme_name}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{t["accent"]}"/>
      <stop offset="100%" stop-color="{t["accent2"]}"/>
    </linearGradient>
  </defs>

  <rect width="840" height="196" rx="16" fill="{t["bg"]}" stroke="{t["border"]}" stroke-width="1"/>
  <rect x="1" y="1" width="838" height="194" rx="15" fill="url(#dots-{theme_name})"/>
  <rect x="1" y="1" width="838" height="194" rx="15" fill="url(#glow1-{theme_name})"/>
  <rect x="1" y="1" width="838" height="194" rx="15" fill="url(#glow2-{theme_name})"/>
  <rect x="32" y="0" width="136" height="3" rx="1.5" fill="url(#accent-bar-{theme_name})"/>

  <text x="32" y="42" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="14" font-weight="600" letter-spacing="1.2">{esc(org_line)}</text>

  <text x="32" y="96" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="42" font-weight="700" letter-spacing="-0.8">{esc(name)} <tspan dx="10" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="20" font-weight="500" letter-spacing="0">@{esc(username)}</tspan></text>

  <text x="32" y="133" fill="{t["accent"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="22" font-weight="600">{esc(headline)}</text>

  <text x="32" y="166" fill="{t["sub"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="17.5" font-weight="400">{esc(supporting_line)}</text>
</svg>
'''


def render_summary_svg(metrics: ProfileMetrics, theme_name: str) -> str:
    """Render a compact, accurately scoped public GitHub activity summary card."""
    if theme_name not in THEMES:
        raise ValidationError(f"Unsupported theme: {theme_name}")
    t = THEMES[theme_name]

    columns = [
        (
            "FEATURED UPSTREAM PRS",
            f"{fmt_count(metrics.featured_merged_total)} merged",
            "dex · agentipy · PyHealth · raen",
        ),
        (
            "PUBLIC ACTIVITY (1Y)",
            fmt_count(metrics.contributions_1y),
            "Rolling 12-month calendar",
        ),
        (
            "UPSTREAM BUG REPORTS",
            f"{fmt_count(metrics.goose_issues)} filed",
            "aaif-goose/goose",
        ),
    ]

    col_svg: list[str] = []
    col_w = 264
    for idx, (label, value, scope) in enumerate(columns):
        x = 32 + idx * col_w
        if idx > 0:
            col_svg.append(
                f'  <line x1="{x - 16}" y1="28" x2="{x - 16}" y2="108" stroke="{t["border"]}" stroke-width="1"/>'
            )
        col_svg.append(
            f'  <text x="{x}" y="42" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="13.5" font-weight="600" letter-spacing="0.6">{esc(label)}</text>'
        )
        col_svg.append(
            f'  <text x="{x}" y="80" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Helvetica, Arial, sans-serif" font-size="31" font-weight="700">{esc(value)}</text>'
        )
        col_svg.append(
            f'  <text x="{x}" y="106" fill="{t["sub"]}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Helvetica, Arial, sans-serif" font-size="14.5">{esc(scope)}</text>'
        )

    footer = f"Periodically updated public GitHub activity · Updated {metrics.updated_at_utc}"
    aria_label = (
        f"Public GitHub summary: {metrics.featured_merged_total} merged PRs across featured repositories, "
        f"{metrics.contributions_1y} contributions in the rolling 12-month calendar, "
        f"{metrics.goose_issues} bug reports filed on aaif-goose/goose. Updated {metrics.updated_at_utc}."
    )

    return f'''<svg width="840" height="168" viewBox="0 0 840 168" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{esc(aria_label)}">
  <rect width="840" height="168" rx="16" fill="{t["card"]}" stroke="{t["border"]}" stroke-width="1"/>
{chr(10).join(col_svg)}
  <line x1="32" y1="126" x2="808" y2="126" stroke="{t["border"]}" stroke-width="1"/>
  <text x="32" y="150" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="13.5">{esc(footer)}</text>
</svg>
'''


def render_oss_markdown(metrics: ProfileMetrics) -> str:
    """Render accessible, mobile-friendly Markdown blocks for featured open-source work."""
    dex_open_note = (
        f" ({pluralize(metrics.dex_open, 'open PR')} under review)"
        if metrics.dex_open > 0
        else ""
    )
    agentipy_open_note = (
        f" ({pluralize(metrics.agentipy_open, 'open PR')})"
        if metrics.agentipy_open > 0
        else ""
    )
    pyhealth_open_note = (
        f" ({pluralize(metrics.pyhealth_open, 'open PR')} under review)"
        if metrics.pyhealth_open > 0
        else ""
    )

    lines = [
        f"*{pluralize(metrics.featured_merged_total, 'merged PR')} across the four featured upstream codebases below, plus {pluralize(metrics.goose_issues, 'reproducible bug report')} on Goose (updated {metrics.updated_at_utc}).*",
        "",
        f"### [exmergo/dex](https://github.com/exmergo/dex) — {pluralize(metrics.dex_merged, 'merged PR')}{dex_open_note}",
        "Open-source Python, SQL, and dbt data-engineering toolkit. Contributed incremental test scaffolding fixes, Cube token scope enforcement, semantic layer validation, YAML variable reference discovery, and DuckDB end-to-end test coverage.",
        f"- **Selected PRs:** [Cube `dex_scopes` enforcement (#1175)](https://github.com/exmergo/dex/pull/1175) · [Incremental test scaffold fix (#1144)](https://github.com/exmergo/dex/pull/1144)",
        f"- **Verify:** [All merged PRs by @{metrics.username}](https://github.com/exmergo/dex/pulls?q=is%3Apr+author%3A{metrics.username}+is%3Amerged)",
        "",
        f"### [niceberginc/agentipy](https://github.com/niceberginc/agentipy) — {pluralize(metrics.agentipy_merged, 'merged PR')}{agentipy_open_note}",
        "Python toolkit for connecting AI agents to Solana protocols and data sources. Contributed Windows `asyncio`/`aiodns` compatibility, Jupiter and CoinGecko integrations, Solana RPC response handling, LangChain/RugCheck tooling, a Discord MCP server, and examples.",
        f"- **Selected PRs:** [Windows `aiodns` event-loop fix (#69)](https://github.com/niceberginc/agentipy/pull/69) · [Discord MCP server (#137)](https://github.com/niceberginc/agentipy/pull/137)",
        f"- **Verify:** [All merged PRs by @{metrics.username}](https://github.com/niceberginc/agentipy/pulls?q=is%3Apr+author%3A{metrics.username}+is%3Amerged)",
        "",
        f"### [sunlabuiuc/PyHealth](https://github.com/sunlabuiuc/PyHealth) — {pluralize(metrics.pyhealth_merged, 'merged PR')}{pyhealth_open_note}",
        "Open-source deep learning framework for healthcare and electronic health records. Implemented and integrated published clinical models—BEHRT, BiteNet, UDC, and DescEmb—in `pyhealth.models`, plus a group-conditional fair conformal predictor in `pyhealth.calib`.",
        f"- **Selected PRs:** [BEHRT EHR model integration (#1517)](https://github.com/sunlabuiuc/PyHealth/pull/1517) · [DescEmb code-embedding model integration (#1530)](https://github.com/sunlabuiuc/PyHealth/pull/1530)",
        f"- **Verify:** [All merged PRs by @{metrics.username}](https://github.com/sunlabuiuc/PyHealth/pulls?q=is%3Apr+author%3A{metrics.username}+is%3Amerged)",
        "",
        f"### [bshelby88/raen-bounties](https://github.com/bshelby88/raen-bounties) — {pluralize(metrics.raen_merged, 'merged PR')}",
        "Python CLI for x402 micropayment workflows. Replaced ad-hoc EIP-712/EIP-3009 signing with standards-compliant typed-data signing via `eth-account`, fixing challenge handling, nonce consistency, spending limits, and test coverage.",
        "- **Verify:** [Standards-compliant EIP-3009 signing & x402 handling (#28)](https://github.com/bshelby88/raen-bounties/pull/28)",
        "",
        f"### [aaif-goose/goose](https://github.com/aaif-goose/goose) — {pluralize(metrics.goose_issues, 'bug report')} (issues, not code PRs)",
        "Open-source developer agent CLI. Filed reproducible CLI bug reports with isolated scripts, synthetic fixtures, and logs covering a session HTML export panic when piped to `head` and misleading `--resume` flag help output.",
        f"- **Verify:** [Session HTML export pipe panic (#13296)](https://github.com/aaif-goose/goose/issues/13296) · [Unsupported `--resume` help output (#13547)](https://github.com/aaif-goose/goose/issues/13547)",
    ]
    return "\n".join(lines)


def render_activity_markdown(metrics: ProfileMetrics) -> str:
    """Render accessible plain-text summary matching summary-*.svg."""
    return (
        f"Public GitHub summary (updated {metrics.updated_at_utc}): "
        f"**{pluralize(metrics.featured_merged_total, 'merged PR')}** across the four featured upstream repositories, "
        f"**{fmt_count(metrics.contributions_1y)} contributions** in the rolling 12-month public calendar, and "
        f"**{pluralize(metrics.goose_issues, 'bug report')}** filed on `aaif-goose/goose`."
    )


def update_marked_section(
    document: str, start_marker: str, end_marker: str, replacement: str
) -> str:
    """Replace content strictly between start_marker and end_marker while preserving surrounding text."""
    start_idx = document.find(start_marker)
    end_idx = document.find(end_marker)
    if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
        raise ValidationError(
            f"Missing or invalid marker pair: {start_marker!r} .. {end_marker!r}"
        )
    before = document[: start_idx + len(start_marker)]
    after = document[end_idx:]
    return f"{before}\n{replacement.rstrip()}\n{after}"


def validate_svg_xml(svg_text: str, name: str) -> None:
    """Validate that generated SVG is well-formed XML with an <svg> root."""
    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as exc:
        raise ValidationError(f"Generated SVG '{name}' is invalid XML: {exc}") from exc
    if not root.tag.endswith("svg"):
        raise ValidationError(f"Generated SVG '{name}' root tag is {root.tag!r}, expected 'svg'.")


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def generate_outputs(
    metrics: ProfileMetrics,
    readme_text: str,
) -> tuple[dict[str, str], str]:
    """Generate and validate all SVG assets and updated README content in memory."""
    svg_files: dict[str, str] = {}
    for mode in ("dark", "light"):
        hero_name = f"hero-{mode}.svg"
        summary_name = f"summary-{mode}.svg"
        hero_svg = render_hero_svg(mode, username=metrics.username)
        summary_svg = render_summary_svg(metrics, mode)
        validate_svg_xml(hero_svg, hero_name)
        validate_svg_xml(summary_svg, summary_name)
        svg_files[hero_name] = hero_svg
        svg_files[summary_name] = summary_svg

    updated_readme = update_marked_section(
        readme_text, OSS_START_MARKER, OSS_END_MARKER, render_oss_markdown(metrics)
    )
    updated_readme = update_marked_section(
        updated_readme,
        ACTIVITY_START_MARKER,
        ACTIVITY_END_MARKER,
        render_activity_markdown(metrics),
    )
    return svg_files, updated_readme


def write_outputs_safely(
    base_dir: Path, svg_files: dict[str, str], updated_readme: str
) -> None:
    """Atomically write validated SVG assets and README.md."""
    assets_dir = base_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in svg_files.items():
        _atomic_write_text(assets_dir / filename, content)
    _atomic_write_text(base_dir / "README.md", updated_readme)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Alhibb GitHub profile assets and README sections.")
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root directory.",
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        default=None,
        help="Optional offline JSON file matching the GitHub GraphQL 'data' shape.",
    )
    parser.add_argument(
        "--timestamp",
        type=str,
        default=None,
        help="Optional explicit UTC timestamp string (e.g. '2026-11-19 11:46 UTC').",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    base_dir: Path = args.base_dir
    readme_path = base_dir / "README.md"
    if not readme_path.exists():
        raise ValidationError(f"README.md not found at {readme_path}")

    if args.input_json is not None:
        raw_data = json.loads(args.input_json.read_text(encoding="utf-8"))
    else:
        token = os.environ.get("GITHUB_TOKEN", "")
        raw_data = fetch_github_data(PROFILE_USERNAME, token)

    metrics = normalize_and_validate(
        raw_data,
        username=PROFILE_USERNAME,
        updated_at_utc=args.timestamp,
    )
    readme_text = readme_path.read_text(encoding="utf-8")
    svg_files, updated_readme = generate_outputs(metrics, readme_text)
    write_outputs_safely(base_dir, svg_files, updated_readme)
    print(
        f"Updated {len(svg_files)} SVG assets and README.md for @{metrics.username} "
        f"({metrics.updated_at_utc})."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GitHubAPIError, ValidationError) as err:
        print(f"Error: {err}", file=sys.stderr)
        raise SystemExit(1)
