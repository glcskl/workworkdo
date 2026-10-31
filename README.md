# workworkdo — WorkDo

WorkDo is a SaaS product for small businesses: staff records, timesheets, shift schedules, payroll, finance and budgeting, with roles and an audit trail. The service runs at [workdo.ru](https://workdo.ru).

This repository holds the project documentation and the tooling that publishes the commit dashboard for the WorkDo codebase.

## What WorkDo does

| Module | Purpose |
| --- | --- |
| Staff | Employee records, positions and access roles |
| Timesheets | Shifts, schedules and worked hours |
| Payroll | Salary calculation from shifts, rates and entries |
| Finance | Income, expenses and budgets |
| Audit | History of changes and user actions |

## Dashboard

The dashboard is built four times a day from the commit metadata of the WorkDo codebase and published at [glcskl.github.io/workworkdo](https://glcskl.github.io/workworkdo/).

- `scripts/fetch_commits.py` reads the commit list from the source repository through the GitHub API
- `data/commits.json` keeps the last snapshot and is committed only when the snapshot actually changes
- `_site/` is generated on every run and is not stored in the repository

If the source is unreachable, the last good snapshot is served with a notice instead of failing the run.

## Links

- Product: [workdo.ru](https://workdo.ru)
- Author: [@glebentired](https://t.me/glebentired)

## Notes

WorkDo is a private commercial product, so the application source is not published here. This repository holds documentation and the tooling that publishes the commit dashboard.
