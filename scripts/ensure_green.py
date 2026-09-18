#!/usr/bin/env python3
"""Ensure the contribution graph never has an empty day.

If any day (UTC) in the last LOOKBACK_DAYS has no commit authored as the
configured contribution account, this script rewrites/backfills a commit for
that day (with real content appended to data/history.csv) so the GitHub
activity cell stays green even when the scheduled Actions workflow didn't run.

GitHub colours a cell by the commit *author* date, so backdated commits pushed
now still fill the matching past day.

USAGE:
    python3 scripts/ensure_green.py [--dry-run] [--lookback N]
Options override the LOOKBACK_DAYS env var.

Env:
    LOOKBACK_DAYS    how many days back to scan (default 60)
    GIT_AUTHOR_NAME  contribution author name  (default glcskl)
    GIT_AUTHOR_EMAIL contribution author email (default 188385208+glcskl@users.noreply.github.com)
    BRANCH           branch to push (default main)
"""
import argparse
import csv
import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRANCH = os.environ.get("BRANCH", "main")
AUTHOR_NAME = os.environ.get("GIT_AUTHOR_NAME", "glcskl")
AUTHOR_EMAIL = os.environ.get(
    "GIT_AUTHOR_EMAIL", "188385208+glcskl@users.noreply.github.com"
)
DEFAULT_LOOKBACK = int(os.environ.get("LOOKBACK_DAYS", "60"))

VARIANTS = [
    "chore(workworkdo): refresh activity snapshot",
    "chore(workworkdo): rebuild commit dashboard",
    "chore(workworkdo): update feed cache",
    "chore(workworkdo): sync remote snapshot",
    "chore(workworkdo): regenerate daily grid",
    "chore(workworkdo): bump workdo radar",
    "chore(workworkdo): refresh metadata",
    "chore(workworkdo): update dashboard assets",
]


def git(*args, check=True, env=None):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    p = subprocess.run(
        ["git", "-C", ROOT, *list(args)],
        capture_output=True,
        text=True,
        env=full_env,
    )
    if check and p.returncode:
        sys.stderr.write(p.stderr)
        raise SystemExit(2)
    return p


def existing_days():
    """Return the set of ISO dates that already have a commit authored by
    AUTHOR_EMAIL on the remote branch."""
    p = git("log", f"origin/{BRANCH}", "--format=%aI%x09%ae", check=False)
    days = set()
    if p.returncode != 0:
        return days
    for line in p.stdout.splitlines():
        raw_date, email = line.split("\t", 1)
        if email != AUTHOR_EMAIL:
            continue
        try:
            dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        except ValueError:
            continue
        days.add(dt.date().isoformat())
    return days


def missing_days(lookback):
    present = existing_days()
    today = date.today()
    return [
        today - timedelta(days=i)
        for i in range(lookback)
        if (today - timedelta(days=i)).isoformat() not in present
    ]


def backfill(days, dry_run):
    if not days:
        print("OK: no empty days in the lookback window")
        return 0

    print(f"Missing {len(days)} day(s):")
    for d in days:
        print("  ", d.isoformat())

    if dry_run:
        print("[dry-run] no commits created")
        return 0

    history = os.path.join(ROOT, "data", "history.csv")
    os.makedirs(os.path.dirname(history), exist_ok=True)
    write_header = not os.path.exists(history) or os.path.getsize(history) == 0
    now = datetime.now(timezone.utc).isoformat()

    for d in days:
        stamp = d.strftime("%Y-%m-%dT12:00:00+00:00")
        idx = d.toordinal() % len(VARIANTS)
        msg = VARIANTS[idx]
        with open(history, "a", newline="") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(["timestamp", "message"])
                write_header = False
            w.writerow([stamp, msg])
        env = {"GIT_AUTHOR_DATE": stamp}
        git("add", "data/history.csv")
        git(
            "-c", f"user.name={AUTHOR_NAME}",
            "-c", f"user.email={AUTHOR_EMAIL}",
            "commit", "-q", "-m", msg,
            env=env,
        )
        print("   committed", msg, "dated", d.isoformat())

    git("push", "origin", f"HEAD:{BRANCH}")
    print(f"Pushed {len(days)} backfill commit(s)")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--lookback", type=int, default=DEFAULT_LOOKBACK)
    args = ap.parse_args()

    git("fetch", "origin")
    git("checkout", "-B", BRANCH, f"origin/{BRANCH}")

    days = [d for d in missing_days(args.lookback) if d <= date.today()]
    days.reverse()
    return backfill(days, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())