"""Generate minimalist dark/light card-based SVG assets and refresh README metrics for Alhibb."""

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
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROFILE_USERNAME = os.environ.get("PROFILE_USERNAME", "Alhibb").strip() or "Alhibb"
DISPLAY_NAME = "Ibrahim Rabiu"
HEADLINE = "AI Systems Engineer & Independent Researcher"
SUPPORTING_LINE = "Agent Reliability · Applied AI · Developer Tooling"
ORG_LINE = "OPEN SOURCE · ENGINEERING · RESEARCH"
SUB_ORG_LINE = "Founder, DevClans Solution Ltd  ·  Building AgentConform"

ACTIVITY_START_MARKER = "<!-- ACTIVITY_SUMMARY:START -->"
ACTIVITY_END_MARKER = "<!-- ACTIVITY_SUMMARY:END -->"
METRICS_STATE_FILE = "assets/.metrics-state.json"

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
        "purple_bg": "#2E1065",
        "purple_fg": "#D8B4FE",
        "green_bg": "#052E16",
        "green_fg": "#86EFAC",
        "cyan_bg": "#082F49",
        "cyan_fg": "#7DD3FC",
        "neutral_bg": "#18181B",
        "neutral_fg": "#D4D4D8",
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
        "purple_bg": "#F3E8FF",
        "purple_fg": "#6B21A8",
        "green_bg": "#DCFCE7",
        "green_fg": "#166534",
        "cyan_bg": "#E0F2FE",
        "cyan_fg": "#075985",
        "neutral_bg": "#F4F4F5",
        "neutral_fg": "#3F3F46",
        "glow_opacity": "0.10",
    },
}

PROJECT_CARDS: list[dict[str, Any]] = [
    {
        "slug": "evidenceshift",
        "title": "EvidenceShift",
        "badge": "EVAL RESEARCH",
        "badge_tone": "purple",
        "dot_color": "#A855F7",
        "line1": "Zero-dependency Python LLM evaluation harness for",
        "line2": "conflicting dates, authority, and incomplete evidence.",
        "tags": ["Python", "Stdlib", "Bootstrap Eval", "unittest"],
        "repo": "Alhibb/EvidenceShift",
    },
    {
        "slug": "cloudcompass",
        "title": "CloudCompass AI",
        "badge": "WEB PROTOTYPE",
        "badge_tone": "green",
        "dot_color": "#22C55E",
        "line1": "Visual AWS architecture designer with React Flow,",
        "line2": "AWS Bedrock runtime, Supabase, and diagram export.",
        "tags": ["TypeScript", "Next.js", "React Flow", "Bedrock"],
        "repo": "Alhibb/CloudCompassAI",
    },
    {
        "slug": "tradeguard",
        "title": "TradeGuard",
        "badge": "TESTNET DEMO",
        "badge_tone": "cyan",
        "dot_color": "#22D3EE",
        "line1": "Reviewed Qwen agreement extraction, delivery evidence,",
        "line2": "and Solidity escrow settlement on Monad testnet.",
        "tags": ["JavaScript", "TypeScript", "Solidity", "Qwen"],
        "repo": "Alhibb/metropolis_tradeguard",
    },
    {
        "slug": "tutoring-rag",
        "title": "AI Tutoring RAG",
        "badge": "PROTOTYPE",
        "badge_tone": "neutral",
        "dot_color": "#38BDF8",
        "line1": "Personalized university tutoring portal indexing course",
        "line2": "notes in ChromaDB with Gemini RAG & SQLite storage.",
        "tags": ["Python", "Streamlit", "ChromaDB", "Gemini"],
        "repo": "Alhibb/ai-tutoring-rag",
    },
]

CAPABILITY_ROWS: list[tuple[str, list[str]]] = [
    ("AI & Reliability", ["AI Agents", "Permission Safety", "LLM Eval", "RAG", "PyTorch", "PyHealth"]),
    ("Backend & Tooling", ["Python", "Rust", "MCP Servers", "CLI Tooling", "asyncio", "REST / GraphQL"]),
    ("Data Engineering", ["SQL", "dbt", "DuckDB", "Semantic Validation", "Cube"]),
    ("Web Applications", ["TypeScript", "JavaScript", "Next.js", "React", "Tailwind CSS", "Supabase"]),
    ("Blockchain", ["Solidity", "EIP-712 / EIP-3009", "x402", "Solana RPC", "Monad Testnet"]),
]

GRAPHQL_QUERY = """
query(
  $login: String!,
  $qDexMerged: String!,
  $qDexOpen: String!,
  $qAgentipyMerged: String!,
  $qAgentipyOpen: String!,
  $qPyhealthMerged: String!,
  $qPyhealthOpen: String!,
  $qRaenMerged: String!,
  $qGooseMerged: String!,
  $qGooseOpen: String!,
  $qGooseIssues: String!
) {
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
  gooseMerged: search(query: $qGooseMerged, type: ISSUE, first: 1) {
    issueCount
  }
  gooseOpen: search(query: $qGooseOpen, type: ISSUE, first: 1) {
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
    goose_merged: int
    goose_open: int
    goose_issues: int
    updated_at_utc: str

    @property
    def featured_merged_total(self) -> int:
        return (
            self.dex_merged
            + self.agentipy_merged
            + self.pyhealth_merged
            + self.raen_merged
            + self.goose_merged
        )

    @property
    def featured_open_total(self) -> int:
        return (
            self.dex_open
            + self.agentipy_open
            + self.pyhealth_open
            + self.goose_open
        )

    def fingerprint(self) -> dict[str, Any]:
        """Return metrics dictionary excluding timestamp for change detection."""
        data = asdict(self)
        data.pop("updated_at_utc", None)
        return data


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
        "qGooseMerged": f"repo:aaif-goose/goose is:pr author:{username} is:merged",
        "qGooseOpen": f"repo:aaif-goose/goose is:pr author:{username} is:open",
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
        goose_merged=_extract_issue_count(raw_data, "gooseMerged"),
        goose_open=_extract_issue_count(raw_data, "gooseOpen"),
        goose_issues=_extract_issue_count(raw_data, "gooseIssues"),
        updated_at_utc=timestamp.strip(),
    )


def esc(text: Any) -> str:
    return html.escape(str(text if text is not None else ""), quote=True)


def fmt_count(n: int) -> str:
    return f"{n:,}"


def pluralize(count: int, singular: str, plural: str | None = None) -> str:
    word = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {word}"


def _theme(theme_name: str) -> dict[str, str]:
    if theme_name not in THEMES:
        raise ValidationError(f"Unsupported theme: {theme_name}")
    return THEMES[theme_name]


def render_hero_svg(
    theme_name: str,
    *,
    name: str = DISPLAY_NAME,
    username: str = PROFILE_USERNAME,
    headline: str = HEADLINE,
    supporting_line: str = SUPPORTING_LINE,
    org_line: str = ORG_LINE,
    sub_org_line: str = SUB_ORG_LINE,
) -> str:
    t = _theme(theme_name)
    return f'''<svg width="840" height="218" viewBox="0 0 840 218" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{esc(name)} (@{esc(username)}) — {esc(headline)}">
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

  <rect width="840" height="218" rx="16" fill="{t["bg"]}" stroke="{t["border"]}" stroke-width="1"/>
  <rect x="1" y="1" width="838" height="216" rx="15" fill="url(#dots-{theme_name})"/>
  <rect x="1" y="1" width="838" height="216" rx="15" fill="url(#glow1-{theme_name})"/>
  <rect x="1" y="1" width="838" height="216" rx="15" fill="url(#glow2-{theme_name})"/>
  <rect x="32" y="0" width="144" height="3" rx="1.5" fill="url(#accent-bar-{theme_name})"/>

  <text x="32" y="40" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="13.5" font-weight="600" letter-spacing="1.2">{esc(org_line)}</text>
  <text x="32" y="92" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="42" font-weight="700" letter-spacing="-0.8">{esc(name)} <tspan dx="10" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="20" font-weight="500" letter-spacing="0">@{esc(username)}</tspan></text>
  <text x="32" y="128" fill="{t["accent"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="21.5" font-weight="600">{esc(headline)}</text>
  <text x="32" y="158" fill="{t["sub"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="16.5" font-weight="400">{esc(supporting_line)}</text>
  <line x1="32" y1="176" x2="808" y2="176" stroke="{t["border"]}" stroke-width="1"/>
  <text x="32" y="200" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="13" font-weight="500">{esc(sub_org_line)}</text>
</svg>
'''


def _render_half_card(
    theme_name: str,
    *,
    title: str,
    badge: str,
    badge_tone: str,
    dot_color: str,
    line1: str,
    line2: str,
    tags: list[str],
    aria_label: str,
) -> str:
    t = _theme(theme_name)
    badge_bg = t[f"{badge_tone}_bg"]
    badge_fg = t[f"{badge_tone}_fg"]
    badge_w = max(78, int(len(badge) * 7.2 + 20))
    badge_x = 414 - 20 - badge_w

    tag_svg: list[str] = []
    tx = 20
    for tag in tags:
        tw = int(len(tag) * 6.8 + 18)
        if tx + tw > 372:
            break
        tag_svg.append(
            f'  <rect x="{tx}" y="118" width="{tw}" height="22" rx="6" fill="{t["card_inner"]}" stroke="{t["border"]}" stroke-width="1"/>'
        )
        tag_svg.append(
            f'  <text x="{tx + tw / 2:.1f}" y="133" text-anchor="middle" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="10.5" font-weight="500">{esc(tag)}</text>'
        )
        tx += tw + 7

    return f'''<svg width="414" height="156" viewBox="0 0 414 156" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{esc(aria_label)}">
  <rect width="414" height="156" rx="14" fill="{t["card"]}" stroke="{t["border"]}" stroke-width="1"/>
  <circle cx="26" cy="30" r="4.5" fill="{esc(dot_color)}"/>
  <text x="40" y="35" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="16" font-weight="600">{esc(title)}</text>
  <rect x="{badge_x}" y="19" width="{badge_w}" height="22" rx="6" fill="{badge_bg}"/>
  <text x="{badge_x + badge_w / 2:.1f}" y="34" text-anchor="middle" fill="{badge_fg}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="10.5" font-weight="600">{esc(badge)}</text>
  <text x="20" y="69" fill="{t["sub"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="13">{esc(line1)}</text>
  <text x="20" y="89" fill="{t["sub"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="13">{esc(line2)}</text>
  <line x1="20" y1="106" x2="394" y2="106" stroke="{t["border"]}" stroke-width="1"/>
{chr(10).join(tag_svg)}
  <text x="394" y="134" text-anchor="end" fill="{t["muted"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="15">↗</text>
</svg>
'''


def _render_feature_card(
    theme_name: str,
    *,
    title: str,
    subtitle: str,
    badges: list[tuple[str, str]],
    dot_color: str,
    line1: str,
    tags: list[str],
    aria_label: str,
) -> str:
    """Render a sleek full-width spotlight card (840x124) for flagship initiatives."""
    t = _theme(theme_name)

    badge_svg: list[str] = []
    cursor_right = 816
    for text, tone in reversed(badges):
        bw = max(78, int(len(text) * 7.0 + 20))
        bx = cursor_right - bw
        badge_svg.append(
            f'  <rect x="{bx}" y="18" width="{bw}" height="24" rx="6" fill="{t[f"{tone}_bg"]}"/>'
        )
        badge_svg.append(
            f'  <text x="{bx + bw / 2:.1f}" y="34" text-anchor="middle" fill="{t[f"{tone}_fg"]}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="10.5" font-weight="600">{esc(text)}</text>'
        )
        cursor_right = bx - 8

    tag_svg: list[str] = []
    tx = 24
    for tag in tags:
        tw = int(len(tag) * 6.9 + 18)
        if tx + tw > 780:
            break
        tag_svg.append(
            f'  <rect x="{tx}" y="88" width="{tw}" height="22" rx="6" fill="{t["card_inner"]}" stroke="{t["border"]}" stroke-width="1"/>'
        )
        tag_svg.append(
            f'  <text x="{tx + tw / 2:.1f}" y="103" text-anchor="middle" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="10.5" font-weight="500">{esc(tag)}</text>'
        )
        tx += tw + 8

    return f'''<svg width="840" height="124" viewBox="0 0 840 124" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{esc(aria_label)}">
  <rect width="840" height="124" rx="14" fill="{t["card"]}" stroke="{t["border"]}" stroke-width="1"/>
  <circle cx="30" cy="30" r="4.5" fill="{esc(dot_color)}"/>
  <text x="44" y="35" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="16.5" font-weight="600">{esc(title)} <tspan dx="8" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="12" font-weight="500">{esc(subtitle)}</tspan></text>
{chr(10).join(badge_svg)}
  <text x="24" y="66" fill="{t["sub"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="13.5">{esc(line1)}</text>
  <line x1="24" y1="78" x2="816" y2="78" stroke="{t["border"]}" stroke-width="1"/>
{chr(10).join(tag_svg)}
  <text x="816" y="104" text-anchor="end" fill="{t["muted"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="15">↗</text>
</svg>
'''


def render_oss_cards(metrics: ProfileMetrics, theme_name: str) -> dict[str, str]:
    """Render clickable minimalist cards for each featured open-source codebase."""
    goose_badges: list[tuple[str, str]] = [
        (f"{metrics.goose_merged} MERGED PR" if metrics.goose_merged == 1 else f"{metrics.goose_merged} MERGED PRS", "purple"),
    ]
    if metrics.goose_open > 0:
        goose_badges.append(
            (f"{metrics.goose_open} OPEN PR" if metrics.goose_open == 1 else f"{metrics.goose_open} OPEN PRS", "green")
        )
    goose_badges.append((f"{metrics.goose_issues} BUG REPORTS", "cyan"))

    pyhealth_badge = (
        f"{metrics.pyhealth_merged} MERGED · +{metrics.pyhealth_open} OPEN"
        if metrics.pyhealth_open > 0
        else f"{metrics.pyhealth_merged} MERGED"
    )

    return {
        f"oss-goose-{theme_name}.svg": _render_feature_card(
            theme_name,
            title="aaif-goose/goose",
            subtitle="AI Agent Infrastructure · Rust",
            badges=goose_badges,
            dot_color="#22D3EE",
            line1="CLI reliability, session management, non-interactive execution, confirmation safeguards & regression testing.",
            tags=["Rust", "CLI Reliability", "Safeguards", "Regression Tests"],
            aria_label=(
                f"aaif-goose/goose — {metrics.goose_merged} merged PR, {metrics.goose_open} open PR, "
                f"{metrics.goose_issues} bug reports by @{metrics.username}"
            ),
        ),
        f"oss-dex-{theme_name}.svg": _render_half_card(
            theme_name,
            title="exmergo/dex",
            badge=f"{metrics.dex_merged} MERGED",
            badge_tone="purple",
            dot_color="#3572A5",
            line1="Incremental test scaffolding, Cube token scope checks,",
            line2="semantic validation & DuckDB end-to-end coverage.",
            tags=["Python", "SQL", "dbt", "DuckDB"],
            aria_label=f"exmergo/dex — {metrics.dex_merged} merged PRs by @{metrics.username}",
        ),
        f"oss-agentipy-{theme_name}.svg": _render_half_card(
            theme_name,
            title="niceberginc/agentipy",
            badge=f"{metrics.agentipy_merged} MERGED",
            badge_tone="purple",
            dot_color="#22D3EE",
            line1="Windows aiodns compatibility, Jupiter/CoinGecko APIs,",
            line2="Solana RPC handling, RugCheck & Discord MCP server.",
            tags=["Solana", "MCP", "asyncio", "LangChain"],
            aria_label=f"niceberginc/agentipy — {metrics.agentipy_merged} merged PRs by @{metrics.username}",
        ),
        f"oss-pyhealth-{theme_name}.svg": _render_half_card(
            theme_name,
            title="sunlabuiuc/PyHealth",
            badge=pyhealth_badge,
            badge_tone="purple",
            dot_color="#A855F7",
            line1="Integrated clinical EHR & disease-graph models (BEHRT,",
            line2="BiteNet, UDC, DescEmb & more) + fair conformal calib.",
            tags=["PyTorch", "EHR Models", "Conformal"],
            aria_label=f"sunlabuiuc/PyHealth — {metrics.pyhealth_merged} merged PRs by @{metrics.username}",
        ),
        f"oss-raen-{theme_name}.svg": _render_half_card(
            theme_name,
            title="bshelby88/raen-bounties",
            badge=f"{metrics.raen_merged} MERGED",
            badge_tone="purple",
            dot_color="#22C55E",
            line1="Standards-compliant EIP-712/EIP-3009 signing via",
            line2="eth-account, x402 challenge handling & test suite.",
            tags=["Python CLI", "EIP-3009", "x402"],
            aria_label=f"bshelby88/raen-bounties — {metrics.raen_merged} merged PR by @{metrics.username}",
        ),
    }


def render_project_cards(theme_name: str) -> dict[str, str]:
    """Render clickable minimalist cards for AgentConform flagship research and four curated repos."""
    cards: dict[str, str] = {
        f"proj-agentconform-{theme_name}.svg": _render_feature_card(
            theme_name,
            title="AgentConform",
            subtitle="Independent Agent Security Research",
            badges=[("FLAGSHIP RESEARCH", "purple")],
            dot_color="#A855F7",
            line1="Regression testing for permission repairs in open-source coding agents—verifying fixes keep unrelated boundaries intact.",
            tags=["Agent Reliability", "Permission Safety", "Regression Testing", "Research Website"],
            aria_label="AgentConform — Flagship research initiative on permission repair regression testing for open-source coding agents",
        )
    }
    for p in PROJECT_CARDS:
        cards[f"proj-{p['slug']}-{theme_name}.svg"] = _render_half_card(
            theme_name,
            title=p["title"],
            badge=p["badge"],
            badge_tone=p["badge_tone"],
            dot_color=p["dot_color"],
            line1=p["line1"],
            line2=p["line2"],
            tags=p["tags"],
            aria_label=f"{p['title']} ({p['badge']}) — {p['repo']}",
        )
    return cards


def render_stack_svg(theme_name: str) -> str:
    """Render a minimalist card showing curated technical capabilities."""
    t = _theme(theme_name)
    rows_svg: list[str] = []
    for idx, (category, items) in enumerate(CAPABILITY_ROWS):
        y = 40 + idx * 38
        if idx > 0:
            rows_svg.append(
                f'  <line x1="24" y1="{y - 20}" x2="816" y2="{y - 20}" stroke="{t["border"]}" stroke-width="1"/>'
            )
        rows_svg.append(
            f'  <text x="24" y="{y + 4}" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Helvetica, Arial, sans-serif" font-size="13.5" font-weight="600">{esc(category)}</text>'
        )
        px = 186
        for item in items:
            pw = int(len(item) * 6.9 + 20)
            rows_svg.append(
                f'  <rect x="{px}" y="{y - 12}" width="{pw}" height="24" rx="6" fill="{t["card_inner"]}" stroke="{t["border"]}" stroke-width="1"/>'
            )
            rows_svg.append(
                f'  <text x="{px + pw / 2:.1f}" y="{y + 4}" text-anchor="middle" fill="{t["sub"]}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="11" font-weight="500">{esc(item)}</text>'
            )
            px += pw + 8

    height = 224
    return f'''<svg width="840" height="{height}" viewBox="0 0 840 {height}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Technical capabilities across AI &amp; Reliability, Backend &amp; Tooling, Data Engineering, Web Applications, and Blockchain">
  <rect width="840" height="{height}" rx="16" fill="{t["card"]}" stroke="{t["border"]}" stroke-width="1"/>
{chr(10).join(rows_svg)}
</svg>
'''


def render_summary_svg(metrics: ProfileMetrics, theme_name: str) -> str:
    t = _theme(theme_name)
    columns = [
        (
            "FEATURED UPSTREAM PRS",
            f"{fmt_count(metrics.featured_merged_total)} merged",
            "goose · dex · agentipy · PyHealth · raen",
        ),
        (
            "PUBLIC ACTIVITY (1Y)",
            fmt_count(metrics.contributions_1y),
            "Rolling 12-month calendar",
        ),
        (
            "OPEN PRS & REPORTS",
            f"{metrics.featured_open_total} open · {metrics.goose_issues} reports",
            "Active PRs + Goose bug reports",
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
            f'  <text x="{x}" y="42" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="13" font-weight="600" letter-spacing="0.6">{esc(label)}</text>'
        )
        col_svg.append(
            f'  <text x="{x}" y="80" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Helvetica, Arial, sans-serif" font-size="27" font-weight="700">{esc(value)}</text>'
        )
        col_svg.append(
            f'  <text x="{x}" y="106" fill="{t["sub"]}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Helvetica, Arial, sans-serif" font-size="13">{esc(scope)}</text>'
        )

    footer = f"Periodically updated public GitHub activity · Updated {metrics.updated_at_utc}"
    aria_label = (
        f"Public GitHub summary: {metrics.featured_merged_total} merged PRs across 5 featured repositories, "
        f"{metrics.contributions_1y} contributions in the rolling 12-month calendar, "
        f"{metrics.featured_open_total} open PRs and {metrics.goose_issues} bug reports on aaif-goose/goose. "
        f"Updated {metrics.updated_at_utc}."
    )

    return f'''<svg width="840" height="168" viewBox="0 0 840 168" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{esc(aria_label)}">
  <rect width="840" height="168" rx="16" fill="{t["card"]}" stroke="{t["border"]}" stroke-width="1"/>
{chr(10).join(col_svg)}
  <line x1="32" y1="126" x2="808" y2="126" stroke="{t["border"]}" stroke-width="1"/>
  <text x="32" y="150" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="13.5">{esc(footer)}</text>
</svg>
'''


def render_activity_markdown(metrics: ProfileMetrics) -> str:
    return (
        f"<sub>Updated {metrics.updated_at_utc} · "
        f"<strong>{pluralize(metrics.featured_merged_total, 'merged PR')}</strong> across 5 featured upstream projects "
        f"(<code>exmergo/dex</code>: {metrics.dex_merged}, <code>agentipy</code>: {metrics.agentipy_merged}, "
        f"<code>PyHealth</code>: {metrics.pyhealth_merged}, <code>goose</code>: {metrics.goose_merged}, "
        f"<code>raen-bounties</code>: {metrics.raen_merged}) · "
        f"<strong>{fmt_count(metrics.contributions_1y)}</strong> rolling-year public contributions · "
        f"<strong>{pluralize(metrics.featured_open_total, 'open PR')}</strong> &amp; "
        f"<strong>{pluralize(metrics.goose_issues, 'Goose bug report')}</strong>.</sub>"
    )


def update_marked_section(
    document: str, start_marker: str, end_marker: str, replacement: str
) -> str:
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


def load_previous_fingerprint(base_dir: Path) -> dict[str, Any] | None:
    state_path = base_dir / METRICS_STATE_FILE
    if not state_path.exists():
        return None
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def generate_outputs(
    metrics: ProfileMetrics,
    readme_text: str,
) -> tuple[dict[str, str], str]:
    svg_files: dict[str, str] = {}
    for mode in ("dark", "light"):
        batch: dict[str, str] = {
            f"hero-{mode}.svg": render_hero_svg(mode, username=metrics.username),
            f"stack-{mode}.svg": render_stack_svg(mode),
            f"summary-{mode}.svg": render_summary_svg(metrics, mode),
        }
        batch.update(render_oss_cards(metrics, mode))
        batch.update(render_project_cards(mode))
        for filename, svg_text in batch.items():
            validate_svg_xml(svg_text, filename)
            svg_files[filename] = svg_text

    updated_readme = update_marked_section(
        readme_text,
        ACTIVITY_START_MARKER,
        ACTIVITY_END_MARKER,
        render_activity_markdown(metrics),
    )
    return svg_files, updated_readme


def write_outputs_safely(
    base_dir: Path,
    svg_files: dict[str, str],
    updated_readme: str,
    metrics: ProfileMetrics,
) -> None:
    assets_dir = base_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in svg_files.items():
        _atomic_write_text(assets_dir / filename, content)
    _atomic_write_text(
        base_dir / METRICS_STATE_FILE,
        json.dumps(metrics.fingerprint(), indent=2, sort_keys=True) + "\n",
    )
    _atomic_write_text(base_dir / "README.md", updated_readme)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Alhibb GitHub profile card UI and README metrics.")
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
        help="Optional explicit UTC timestamp string (e.g. '2026-11-27 11:46 UTC').",
    )
    parser.add_argument(
        "--skip-if-unchanged",
        action="store_true",
        help="Skip rewriting assets and timestamp when metrics match assets/.metrics-state.json.",
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

    if args.skip_if_unchanged and load_previous_fingerprint(base_dir) == metrics.fingerprint():
        print(f"No metric changes for @{metrics.username}; skipping timestamp-only update.")
        return 0

    readme_text = readme_path.read_text(encoding="utf-8")
    svg_files, updated_readme = generate_outputs(metrics, readme_text)
    write_outputs_safely(base_dir, svg_files, updated_readme, metrics)
    print(
        f"Updated {len(svg_files)} SVG card assets and README.md for @{metrics.username} "
        f"({metrics.updated_at_utc})."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GitHubAPIError, ValidationError) as err:
        print(f"Error: {err}", file=sys.stderr)
        raise SystemExit(1)
