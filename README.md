# workworkdo

A 3x-daily-updated dashboard that watches the commit activity of a private work
repository and renders it as a GitHub-style contribution grid plus a live
commit feed. It also keeps the owner's contribution graph solid green.

- **data/commits.json** — cached snapshot of the latest commits (source: `ykr0p/ykr0p-new_arch_workdo_w`).
- **_site/index.html** — the generated dashboard (grid + commit history + authors).
- **data/history.csv** — timestamped entries written on each refreshed run.

## How it works

A scheduled GitHub Actions workflow (`refresh-workworkdo`) runs 3x a day. It:

1. Calls the GitHub Commits API for the target repo (private → needs a token).
2. Regenerates `_site/index.html` and `data/commits.json`.
3. Writes a row to `data/history.csv` on every run, then pushes the snapshot.

Every scheduled run produces a commit (3/day, no gap days), so the contribution
graph stays a solid dark green while each commit carries actual dashboard data.

## Env / secrets

| Key | Meaning |
| --- | --- |
| `GITHUB_TOKEN` / `GH_TOKEN` | read scope for fetching the private target repo |
| `TARGET_REPO` | `owner/name` of the watched repository |
| `RADAR_AUTHOR_*` | author identity of the dashboard commits |

The workflow uses the secret `GIT_DASH_TOKEN` (a PAT with read access to the
target repo) to fetch commits.

## Local run

```bash
GITHUB_TOKEN=$(gh auth token) python3 scripts/fetch_commits.py
python3 scripts/update_history.py 1.0 "local refresh"
```
