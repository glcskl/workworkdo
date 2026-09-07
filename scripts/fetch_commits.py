#!/usr/bin/env python3
"""Commit-radar: fetch real commits from a target repo and build a dashboard.

Reads GITHUB_TOKEN (or GH_TOKEN) env var when the target repo is private.
Generates data/commits.json and _site/index.html.
"""
import json
import os
import subprocess
import sys
import urllib.request
from collections import Counter, OrderedDict
from datetime import date, datetime, timedelta

TARGET = os.environ.get("TARGET_REPO", "ykr0p/ykr0p-new_arch_workdo_w")
PER_PAGE = 100
MAX_PAGES = 10
AUTHOR_NAME = os.environ.get("RADAR_AUTHOR_NAME", "glcskl-bot")
AUTHOR_EMAIL = os.environ.get(
    "RADAR_AUTHOR_EMAIL", "188385208+glcskl@users.noreply.github.com"
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STYLES = """
<style>
 body { font-family: -apple-system, system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 16px; color: #222; }
 h1 { font-size: 22px; } h2 { font-size: 16px; margin-top: 32px; }
 .grid { display: flex; gap: 3px; }
 .col { display: flex; flex-direction: column; gap: 3px; }
 .cell { width: 12px; height: 12px; border-radius: 2px; background: #ebedf0; }
 .cell.l1 { background: #c6e48b; } .cell.l2 { background: #7bc96f; }
 .cell.l3 { background: #196c2e; } .cell.l4 { background: #0a4d1e; }
 ol { list-style: none; padding: 0; }
 li { padding: 6px 0; border-bottom: 1px solid #eee; font-size: 14px; }
 code { color: #444; margin-right: 8px; } time { color: #888; margin-right: 8px; }
 .msg { color: #111; } em { color: #999; }
 table { border-collapse: collapse; } td, th { border: 1px solid #ddd; padding: 6px 12px; text-align: left; }
 .meta { color: #777; font-size: 13px; }
</style>
"""


def api(url: str):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "commit-radar")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_commits():
    commits = []
    page = 1
    while page <= MAX_PAGES:
        url = f"https://api.github.com/repos/{TARGET}/commits?per_page={PER_PAGE}&page={page}"
        batch = api(url)
        if not batch:
            break
        for c in batch:
            commits.append(
                {
                    "sha": c["sha"][:10],
                    "date": c["commit"]["author"]["date"],
                    "message": (c["commit"]["message"] or "").split("\n")[0],
                    "author": c["commit"]["author"]["name"],
                }
            )
        if len(batch) < PER_PAGE:
            break
        page += 1
    return commits


def contribution_grid(commits, weeks_count=23):
    counts = Counter()
    for c in commits:
        dt = datetime.fromisoformat(c["date"].replace("Z", "+00:00"))
        counts[dt.date().isoformat()] += 1

    today = date.today()
    start = today - timedelta(days=weeks_count * 7 + 6)
    cursor = start - timedelta(days=start.weekday())
    weeks = []
    while cursor <= today:
        week = []
        for i in range(7):
            d = cursor + timedelta(days=i)
            cnt = counts.get(d.isoformat(), 0)
            week.append(
                {
                    "day": d.isoformat(),
                    "count": cnt,
                    "level": min(cnt, 4),
                }
            )
        weeks.append(week)
        cursor += timedelta(days=7)
    return weeks


def render_grid(weeks):
    html = ["<div class='grid'>"]
    for week in weeks:
        col = ["<div class='col'>"]
        for cell in week:
            cls = f"l{cell['level']}"
            title = f"{cell['day']}: {cell['count']}"
            col.append(f"<div class='cell {cls}' title='{title}'></div>")
        col.append("</div>")
        html.append("".join(col))
    html.append("</div>")
    return "".join(html)


def render_commits(commits):
    rows = []
    for c in commits[:60]:
        rows.append(
            f"<li><code>{c['sha']}</code> <time>{c['date'][:10]}</time> "
            f"<span class='msg'>{c['message']}</span> <em>{c['author']}</em></li>"
        )
    return "<ol>" + "".join(rows) + "</ol>"


def main():
    commits = fetch_commits()
    weeks = contribution_grid(commits)
    authors = Counter(c["author"] for c in commits)
    days = Counter(c["date"][:10] for c in commits)

    grid_html = render_grid(weeks)
    commits_html = render_commits(commits)
    authors_rows = "".join(
        f"<tr><td>{a}</td><td>{n}</td></tr>" for a, n in authors.most_common()
    )

    html = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<title>Commit Radar — {TARGET}</title>"""
    html += STYLES
    html += f"""</head><body>
<h1>Commit Radar</h1>
<p class="meta">Источник: <code>{TARGET}</code> · коммитов: <code>{len(commits)}</code></p>
<h2>Активность (последние ~23 недели)</h2>
{grid_html}
<h2>История коммитов</h2>
{commits_html}
<h2>Авторы</h2>
<table><tr><th>Автор</th><th>Коммитов</th></tr>{authors_rows}</table>
</body></html>"""

    # NOTE: deliberately no "updated" timestamp in the committed files, so a
    # rebuild with identical data produces no diff -> no contribution on days
    # when nothing changed. Only real changes to history.csv / commits push.
    with open(os.path.join(ROOT, "data", "commits.json"), "w") as f:
        json.dump({"source": TARGET, "count": len(commits), "commits": commits}, f, ensure_ascii=False, indent=2)

    with open(os.path.join(ROOT, "_site", "index.html"), "w") as f:
        f.write(html)

    print(f"OK commits={len(commits)} days={len(days)} wrote dashboard")
    return 0


if __name__ == "__main__":
    sys.exit(main())