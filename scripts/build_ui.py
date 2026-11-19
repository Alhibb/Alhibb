import html
import json
import os
import urllib.request
from datetime import datetime, timezone

USERNAME = os.environ.get("GITHUB_ACTOR", "Alhibb")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    followers { totalCount }
    allRepos: repositories(privacy: PUBLIC, ownerAffiliations: OWNER) {
      totalCount
    }
    repositories(
      first: 100
      ownerAffiliations: OWNER
      isFork: false
      privacy: PUBLIC
      orderBy: {field: PUSHED_AT, direction: DESC}
    ) {
      nodes {
        name
        description
        stargazerCount
        pushedAt
        primaryLanguage { name color }
        languages(first: 6, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node { name color }
          }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
    pullRequests(first: 15, orderBy: {field: CREATED_AT, direction: DESC}) {
      totalCount
      nodes {
        title
        state
        createdAt
        repository {
          nameWithOwner
          isPrivate
        }
      }
    }
  }
  dexMerged: search(query: "repo:exmergo/dex is:pr author:Alhibb is:merged", type: ISSUE, first: 1) {
    issueCount
  }
  agentipyMerged: search(query: "repo:niceberginc/agentipy is:pr author:Alhibb is:merged", type: ISSUE, first: 1) {
    issueCount
  }
  pyhealthMerged: search(query: "repo:sunlabuiuc/PyHealth is:pr author:Alhibb is:merged", type: ISSUE, first: 1) {
    issueCount
  }
  pyhealthOpen: search(query: "repo:sunlabuiuc/PyHealth is:pr author:Alhibb is:open", type: ISSUE, first: 1) {
    issueCount
  }
  raenMerged: search(query: "repo:bshelby88/raen-bounties is:pr author:Alhibb is:merged", type: ISSUE, first: 1) {
    issueCount
  }
  gooseIssues: search(query: "repo:aaif-goose/goose is:issue author:Alhibb", type: ISSUE, first: 1) {
    issueCount
  }
}
"""

THEMES = {
    "dark": {
        "bg": "#09090B",
        "card": "#111114",
        "card_inner": "#18181B",
        "border": "#27272A",
        "dot": "#27272A",
        "text": "#FAFAFA",
        "sub": "#A1A1AA",
        "muted": "#71717A",
        "accent": "#22D3EE",
        "accent2": "#A855F7",
        "green": "#22C55E",
        "glow_opacity": "0.18",
        "pill_bg": "#18181B",
        "pill_border": "#27272A",
        "grid_line": "#1F1F23",
    },
    "light": {
        "bg": "#FFFFFF",
        "card": "#FAFAFA",
        "card_inner": "#F4F4F5",
        "border": "#E4E4E7",
        "dot": "#E4E4E7",
        "text": "#09090B",
        "sub": "#52525B",
        "muted": "#71717A",
        "accent": "#0284C7",
        "accent2": "#7C3AED",
        "green": "#16A34A",
        "glow_opacity": "0.10",
        "pill_bg": "#F4F4F5",
        "pill_border": "#E4E4E7",
        "grid_line": "#EBEBEF",
    },
}


def fetch_github_data():
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN is required.")
    payload = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "Alhibb-Bento-UI",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if "errors" in data:
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data["data"]


def esc(text):
    return html.escape(str(text or ""), quote=True)


def trunc(text, limit):
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def fmt_num(n):
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


def rel_date(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        delta = (datetime.now(timezone.utc) - dt).days
        if delta <= 0:
            return "today"
        if delta == 1:
            return "1d ago"
        if delta < 30:
            return f"{delta}d ago"
        return dt.strftime("%b %Y")
    except Exception:
        return ""


def compute_streak(weeks):
    days = [d for w in weeks for d in w["contributionDays"]]
    if not days:
        return 0
    streak = 0
    for d in reversed(days):
        if d["contributionCount"] > 0:
            streak += 1
        elif streak > 0:
            break
    return streak


def render_hero(stats, mode):
    t = THEMES[mode]
    kpis = [
        ("CONTRIBUTIONS (1Y)", fmt_num(stats["contributions"])),
        ("PUBLIC REPOS", str(stats["public_repos"])),
        ("PULL REQUESTS", str(stats["total_prs"])),
        ("STARS EARNED", fmt_num(stats["stars"])),
    ]
    kpi_svg = []
    col_w = 212
    for idx, (label, val) in enumerate(kpis):
        x = 28 + idx * col_w
        if idx > 0:
            kpi_svg.append(f'<line x1="{x - 14}" y1="154" x2="{x - 14}" y2="196" stroke="{t["border"]}" stroke-width="1"/>')
        kpi_svg.append(
            f'<text x="{x}" y="168" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5" letter-spacing="0.8">{label}</text>'
            f'<text x="{x}" y="194" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif" font-size="22" font-weight="700">{esc(val)}</text>'
        )

    return f'''<svg width="900" height="218" viewBox="0 0 900 218" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <pattern id="dots-{mode}" width="20" height="20" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="0.9" fill="{t["dot"]}" opacity="0.7"/>
    </pattern>
    <radialGradient id="glow1-{mode}" cx="85%" cy="15%" r="55%">
      <stop offset="0%" stop-color="{t["accent"]}" stop-opacity="{t["glow_opacity"]}"/>
      <stop offset="100%" stop-color="{t["bg"]}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glow2-{mode}" cx="15%" cy="0%" r="45%">
      <stop offset="0%" stop-color="{t["accent2"]}" stop-opacity="{t["glow_opacity"]}"/>
      <stop offset="100%" stop-color="{t["bg"]}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="accent-bar-{mode}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{t["accent"]}"/>
      <stop offset="100%" stop-color="{t["accent2"]}"/>
    </linearGradient>
  </defs>
  <rect width="900" height="218" rx="16" fill="{t["bg"]}" stroke="{t["border"]}" stroke-width="1"/>
  <rect x="1" y="1" width="898" height="216" rx="15" fill="url(#dots-{mode})"/>
  <rect x="1" y="1" width="898" height="216" rx="15" fill="url(#glow1-{mode})"/>
  <rect x="1" y="1" width="898" height="216" rx="15" fill="url(#glow2-{mode})"/>
  <rect x="28" y="0" width="120" height="2.5" rx="1.25" fill="url(#accent-bar-{mode})"/>

  <!-- Top telemetry bar -->
  <circle cx="34" cy="32" r="4" fill="{t["green"]}">
    <animate attributeName="opacity" values="1;0.3;1" dur="2.4s" repeatCount="indefinite"/>
  </circle>
  <text x="46" y="36" fill="{t["sub"]}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="11.5">~/alhibb  ·  alhibb.devclans.org.ng</text>

  <rect x="742" y="19" width="130" height="24" rx="12" fill="{t["pill_bg"]}" stroke="{t["pill_border"]}" stroke-width="1"/>
  <text x="807" y="35" text-anchor="middle" fill="{t["sub"]}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5">SYNCED · {esc(stats["updated_label"])}</text>

  <!-- Main identity -->
  <text x="28" y="86" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="34" font-weight="700" letter-spacing="-0.8">Ibrahim Rabiu <tspan dx="8" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="16" font-weight="400" letter-spacing="0">@Alhibb</tspan></text>
  <text x="28" y="114" fill="{t["sub"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="14.5">AI &amp; Systems Engineer  ·  Open-Source Contributor  ·  Applied ML &amp; Developer Tooling</text>

  <!-- Hairline divider -->
  <line x1="28" y1="138" x2="872" y2="138" stroke="{t["border"]}" stroke-width="1"/>

  <!-- Live KPI strip -->
  {"".join(kpi_svg)}
</svg>'''


def render_bento(stats, mode):
    t = THEMES[mode]
    weekly = stats["weekly_26"]
    max_w = max(weekly) if weekly and max(weekly) > 0 else 1

    # Build sparkline area chart inside Left Card (x: 24..416, y: 80..186)
    x0, y0, cw, ch = 24, 78, 392, 108
    pts = []
    step = cw / max(len(weekly) - 1, 1)
    for i, val in enumerate(weekly):
        px = x0 + i * step
        py = y0 + ch - (val / max_w) * (ch - 8)
        pts.append((px, py))

    line_d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    area_d = f"{line_d} L {pts[-1][0]:.1f} {y0 + ch} L {pts[0][0]:.1f} {y0 + ch} Z"
    last_x, last_y = pts[-1]

    # Language segmented bar inside Right Card (x: 482..874, y: 76)
    langs = stats["languages"]
    bar_x, bar_y, bar_w, bar_h = 482, 74, 392, 10
    segs = []
    cur_x = bar_x
    for lang in langs:
        sw = max(4.0, (lang["pct"] / 100.0) * bar_w)
        segs.append(f'<rect x="{cur_x:.1f}" y="{bar_y}" width="{sw:.1f}" height="{bar_h}" fill="{esc(lang["color"])}"/>')
        cur_x += sw

    legend_svg = []
    for idx, lang in enumerate(langs[:6]):
        col = idx % 2
        row = idx // 2
        lx = 482 + col * 200
        ly = 112 + row * 26
        legend_svg.append(
            f'<circle cx="{lx + 5}" cy="{ly - 4}" r="4.5" fill="{esc(lang["color"])}"/>'
            f'<text x="{lx + 17}" y="{ly}" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif" font-size="12.5" font-weight="500">{esc(lang["name"])}</text>'
            f'<text x="{lx + 182}" y="{ly}" text-anchor="end" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="11.5">{lang["pct"]:.1f}%</text>'
        )

    pills = ["MCP / Agents", "PyTorch", "Rust / Anchor", "FastAPI / dbt"]
    pill_svg = []
    px_cursor = 482
    for label in pills:
        pw = len(label) * 6.8 + 20
        pill_svg.append(
            f'<rect x="{px_cursor:.0f}" y="200" width="{pw:.0f}" height="24" rx="6" fill="{t["card_inner"]}" stroke="{t["border"]}" stroke-width="1"/>'
            f'<text x="{px_cursor + pw/2:.0f}" y="216" text-anchor="middle" fill="{t["sub"]}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5">{esc(label)}</text>'
        )
        px_cursor += pw + 8

    return f'''<svg width="900" height="248" viewBox="0 0 900 248" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="area-{mode}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{t["accent"]}" stop-opacity="0.32"/>
      <stop offset="100%" stop-color="{t["accent"]}" stop-opacity="0.0"/>
    </linearGradient>
    <clipPath id="lang-clip-{mode}">
      <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5"/>
    </clipPath>
  </defs>

  <!-- Left Bento Card: Velocity -->
  <rect x="0" y="0" width="442" height="248" rx="16" fill="{t["card"]}" stroke="{t["border"]}" stroke-width="1"/>
  <text x="24" y="34" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="13.5" font-weight="600">Contribution Velocity</text>
  <text x="418" y="34" text-anchor="end" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5">26-WEEK PULSE</text>

  <!-- Subtle chart guide lines -->
  <line x1="24" y1="86" x2="416" y2="86" stroke="{t["grid_line"]}" stroke-dasharray="3 4"/>
  <line x1="24" y1="136" x2="416" y2="136" stroke="{t["grid_line"]}" stroke-dasharray="3 4"/>
  <line x1="24" y1="186" x2="416" y2="186" stroke="{t["border"]}"/>

  <!-- Area & Line -->
  <path d="{area_d}" fill="url(#area-{mode})"/>
  <path d="{line_d}" fill="none" stroke="{t["accent"]}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="4" fill="{t["accent"]}"/>

  <!-- Bottom velocity metrics -->
  <text x="24" y="220" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="11">PEAK <tspan fill="{t["text"]}" font-weight="600">{max_w}/wk</tspan>   ·   STREAK <tspan fill="{t["text"]}" font-weight="600">{stats["streak"]}d</tspan>   ·   LAST 6M <tspan fill="{t["text"]}" font-weight="600">{sum(weekly)}</tspan></text>

  <!-- Right Bento Card: Codebase Telemetry -->
  <rect x="458" y="0" width="442" height="248" rx="16" fill="{t["card"]}" stroke="{t["border"]}" stroke-width="1"/>
  <text x="482" y="34" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="13.5" font-weight="600">Codebase Telemetry</text>
  <text x="874" y="34" text-anchor="end" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5">LIVE REPO BYTES</text>

  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5" fill="{t["card_inner"]}"/>
  <g clip-path="url(#lang-clip-{mode})">
    {"".join(segs)}
  </g>

  {"".join(legend_svg)}
  {"".join(pill_svg)}
</svg>'''


def render_shipped(stats, mode):
    t = THEMES[mode]

    # Left Card: Recent Public PRs
    pr_rows = []
    for idx, pr in enumerate(stats["recent_prs"][:4]):
        y = 70 + idx * 49
        state = pr["state"]
        if state == "MERGED":
            badge_bg, badge_fg, label = ("#2E1065", "#C084FC", "MERGED") if mode == "dark" else ("#F3E8FF", "#7E22CE", "MERGED")
        elif state == "OPEN":
            badge_bg, badge_fg, label = ("#052E16", "#4ADE80", "OPEN") if mode == "dark" else ("#DCFCE7", "#15803D", "OPEN")
        else:
            badge_bg, badge_fg, label = (t["card_inner"], t["muted"], "CLOSED")

        if idx > 0:
            pr_rows.append(f'<line x1="24" y1="{y - 14}" x2="418" y2="{y - 14}" stroke="{t["grid_line"]}"/>')
        pr_rows.append(
            f'<rect x="24" y="{y - 4}" width="54" height="18" rx="4" fill="{badge_bg}"/>'
            f'<text x="51" y="{y + 9}" text-anchor="middle" fill="{badge_fg}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="9.5" font-weight="600">{label}</text>'
            f'<text x="88" y="{y + 9}" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif" font-size="12.5" font-weight="600">{esc(trunc(pr["repo"], 30))}</text>'
            f'<text x="418" y="{y + 9}" text-anchor="end" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5">{esc(pr["when"])}</text>'
            f'<text x="24" y="{y + 27}" fill="{t["sub"]}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif" font-size="11.5">{esc(trunc(pr["title"], 56))}</text>'
        )

    # Right Card: Recently Active Repos
    repo_rows = []
    for idx, r in enumerate(stats["recent_repos"][:4]):
        y = 70 + idx * 49
        if idx > 0:
            repo_rows.append(f'<line x1="482" y1="{y - 14}" x2="876" y2="{y - 14}" stroke="{t["grid_line"]}"/>')
        lang_dot = f'<circle cx="786" cy="{y + 5}" r="3.5" fill="{esc(r["lang_color"])}"/>' if r["lang"] else ""
        repo_rows.append(
            f'<text x="482" y="{y + 9}" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif" font-size="12.5" font-weight="600">{esc(trunc(r["name"], 28))}</text>'
            f'{lang_dot}'
            f'<text x="876" y="{y + 9}" text-anchor="end" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5">{esc(r["lang"])}  ·  {esc(r["when"])}</text>'
            f'<text x="482" y="{y + 27}" fill="{t["sub"]}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif" font-size="11.5">{esc(trunc(r["desc"], 56))}</text>'
        )

    return f'''<svg width="900" height="266" viewBox="0 0 900 266" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Left Card: Open-Source PRs -->
  <rect x="0" y="0" width="442" height="266" rx="16" fill="{t["card"]}" stroke="{t["border"]}" stroke-width="1"/>
  <text x="24" y="34" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="13.5" font-weight="600">Recent Pull Requests</text>
  <text x="418" y="34" text-anchor="end" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5">OPEN SOURCE</text>
  {"".join(pr_rows)}

  <!-- Right Card: Active Repos -->
  <rect x="458" y="0" width="442" height="266" rx="16" fill="{t["card"]}" stroke="{t["border"]}" stroke-width="1"/>
  <text x="482" y="34" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="13.5" font-weight="600">Active Repositories</text>
  <text x="876" y="34" text-anchor="end" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5">LATEST PUSHES</text>
  {"".join(repo_rows)}
</svg>'''


def render_oss(stats, mode):
    t = THEMES[mode]
    oss = stats["oss"]
    total_merged = oss["dex_merged"] + oss["agentipy_merged"] + oss["pyhealth_merged"] + oss["raen_merged"]

    merged_bg, merged_fg = ("#2E1065", "#C084FC") if mode == "dark" else ("#F3E8FF", "#7E22CE")
    open_bg, open_fg = ("#052E16", "#4ADE80") if mode == "dark" else ("#DCFCE7", "#15803D")
    issue_bg, issue_fg = ("#082F49", "#38BDF8") if mode == "dark" else ("#E0F2FE", "#0369A1")

    pyhealth_extra = f" +{oss['pyhealth_open']} OPEN" if oss["pyhealth_open"] > 0 else ""

    tiles = [
        {
            "repo": "exmergo/dex",
            "badge": f"{oss['dex_merged']} MERGED",
            "line1": "Python, SQL & dbt tooling: incremental test generation,",
            "line2": "YAML var discovery, semantic checks & DuckDB E2E tests.",
            "color": "#3572A5",
        },
        {
            "repo": "niceberginc/agentipy",
            "badge": f"{oss['agentipy_merged']} MERGED",
            "line1": "Solana agent framework: Jupiter/CoinGecko APIs, Windows",
            "line2": "asyncio fixes, LangChain/RugCheck & Discord MCP server.",
            "color": "#22D3EE",
        },
        {
            "repo": "sunlabuiuc/PyHealth",
            "badge": f"{oss['pyhealth_merged']} MERGED{pyhealth_extra}",
            "line1": "Healthcare AI: BEHRT, BiteNet & UDC clinical EHR models,",
            "line2": "fair conformal predictor (calib) & DescEmb embeddings.",
            "color": "#A855F7",
        },
        {
            "repo": "bshelby88/raen-bounties",
            "badge": f"{oss['raen_merged']} MERGED",
            "line1": "Python CLI: standards-compliant EIP-712/EIP-3009 signing,",
            "line2": "x402 challenge handling, spending limits & test coverage.",
            "color": "#22C55E",
        },
    ]

    tile_svg = []
    for idx, item in enumerate(tiles):
        col = idx % 2
        row = idx // 2
        x = 24 + col * 434
        y = 52 + row * 90
        w = 418
        h = 78
        badge_w = max(72, len(item["badge"]) * 6.5 + 16)
        badge_x = x + w - 14 - badge_w

        tile_svg.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{t["card_inner"]}" stroke="{t["border"]}" stroke-width="1"/>'
            f'<circle cx="{x + 18}" cy="{y + 22}" r="4" fill="{item["color"]}"/>'
            f'<text x="{x + 30}" y="{y + 26}" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif" font-size="13" font-weight="600">{esc(item["repo"])}</text>'
            f'<rect x="{badge_x:.0f}" y="{y + 13}" width="{badge_w:.0f}" height="18" rx="4" fill="{merged_bg}"/>'
            f'<text x="{badge_x + badge_w / 2:.0f}" y="{y + 25.5}" text-anchor="middle" fill="{merged_fg}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="9.5" font-weight="600">{esc(item["badge"])}</text>'
            f'<text x="{x + 16}" y="{y + 48}" fill="{t["sub"]}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif" font-size="11.2">{esc(item["line1"])}</text>'
            f'<text x="{x + 16}" y="{y + 64}" fill="{t["sub"]}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif" font-size="11.2">{esc(item["line2"])}</text>'
        )

    goose_badge = f"{oss['goose_issues']} BUG REPORTS"
    goose_bw = max(86, len(goose_badge) * 6.5 + 16)

    return f'''<svg width="900" height="288" viewBox="0 0 900 288" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="900" height="288" rx="16" fill="{t["card"]}" stroke="{t["border"]}" stroke-width="1"/>
  <text x="24" y="34" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="13.5" font-weight="600">Open-Source Impact</text>
  <text x="876" y="34" text-anchor="end" fill="{t["muted"]}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5">LIVE VERIFIED · {total_merged} FEATURED MERGED PRS</text>

  {"".join(tile_svg)}

  <!-- Bottom compact strip: Goose bug reports -->
  <rect x="24" y="234" width="852" height="36" rx="8" fill="{t["card_inner"]}" stroke="{t["border"]}" stroke-width="1"/>
  <circle cx="42" cy="252" r="4" fill="{t["accent"]}"/>
  <text x="54" y="256" fill="{t["text"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="12.5" font-weight="600">aaif-goose/goose</text>
  <rect x="176" y="243" width="{goose_bw:.0f}" height="18" rx="4" fill="{issue_bg}"/>
  <text x="{176 + goose_bw / 2:.0f}" y="255.5" text-anchor="middle" fill="{issue_fg}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="9.5" font-weight="600">{esc(goose_badge)}</text>
  <text x="{188 + goose_bw:.0f}" y="256" fill="{t["sub"]}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="11.5">Reproducible CLI bug reports: session-export panic piped to head &amp; --resume help flag</text>
</svg>'''


def main():
    gql = fetch_github_data()
    user = gql["user"]
    repos = user["repositories"]["nodes"]
    cal = user["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]

    # Language aggregation across owned non-fork repos
    lang_totals = {}
    lang_colors = {}
    total_stars = 0
    recent_repos = []

    for r in repos:
        total_stars += r["stargazerCount"]
        if r["name"].lower() != USERNAME.lower() and len(recent_repos) < 4:
            pl = r.get("primaryLanguage") or {}
            recent_repos.append(
                {
                    "name": r["name"],
                    "desc": r["description"] or "Active systems & engineering repository",
                    "lang": pl.get("name", ""),
                    "lang_color": pl.get("color", "#71717A"),
                    "when": rel_date(r["pushedAt"]),
                }
            )
        for edge in (r.get("languages") or {}).get("edges", []):
            name = edge["node"]["name"]
            if name in ("HTML", "CSS", "SCSS", "Jupyter Notebook"):
                continue
            lang_totals[name] = lang_totals.get(name, 0) + edge["size"]
            lang_colors[name] = edge["node"].get("color") or "#71717A"

    total_bytes = sum(lang_totals.values()) or 1
    top_langs = sorted(lang_totals.items(), key=lambda kv: kv[1], reverse=True)[:6]
    languages = [
        {"name": n, "pct": (b / total_bytes) * 100.0, "color": lang_colors.get(n, "#71717A")}
        for n, b in top_langs
    ]

    recent_prs = []
    for pr in user["pullRequests"]["nodes"]:
        if pr["repository"]["isPrivate"]:
            continue
        if pr["repository"]["nameWithOwner"].lower() == f"{USERNAME.lower()}/{USERNAME.lower()}":
            continue
        recent_prs.append(
            {
                "repo": pr["repository"]["nameWithOwner"],
                "title": pr["title"],
                "state": pr["state"],
                "when": rel_date(pr["createdAt"]),
            }
        )
        if len(recent_prs) >= 4:
            break

    weekly_26 = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks[-26:]]

    stats = {
        "contributions": cal["totalContributions"],
        "public_repos": user["allRepos"]["totalCount"],
        "total_prs": user["pullRequests"]["totalCount"],
        "stars": total_stars,
        "streak": compute_streak(weeks),
        "weekly_26": weekly_26,
        "languages": languages,
        "recent_prs": recent_prs,
        "recent_repos": recent_repos,
        "oss": {
            "dex_merged": gql["dexMerged"]["issueCount"],
            "agentipy_merged": gql["agentipyMerged"]["issueCount"],
            "pyhealth_merged": gql["pyhealthMerged"]["issueCount"],
            "pyhealth_open": gql["pyhealthOpen"]["issueCount"],
            "raen_merged": gql["raenMerged"]["issueCount"],
            "goose_issues": gql["gooseIssues"]["issueCount"],
        },
        "updated_label": datetime.now(timezone.utc).strftime("%b %d").upper(),
    }

    os.makedirs("assets", exist_ok=True)
    for mode in ("dark", "light"):
        with open(f"assets/hero-{mode}.svg", "w", encoding="utf-8") as f:
            f.write(render_hero(stats, mode))
        with open(f"assets/bento-{mode}.svg", "w", encoding="utf-8") as f:
            f.write(render_bento(stats, mode))
        with open(f"assets/oss-{mode}.svg", "w", encoding="utf-8") as f:
            f.write(render_oss(stats, mode))
        with open(f"assets/shipped-{mode}.svg", "w", encoding="utf-8") as f:
            f.write(render_shipped(stats, mode))

    print("Generated all live Bento SVG assets successfully.")


if __name__ == "__main__":
    main()
