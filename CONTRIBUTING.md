# Contributing

Thanks for proposing a project. This list is a curated catalogue, not a dump of every repository with a security topic.

## What to change

Edit the YAML under `data/`, not `README.md`. CI runs `scripts/build.py --check` and rejects a pull request whose README was edited by hand.

- One repository per pull request.
- Add it to the group file that matches what it is for. The group titles and order are fixed in `scripts/common.py`. AI Skills (skill packs, rules, and playbooks for coding agents) is listed immediately after AI Coding Agents & Harness.
- Required fields: `repo` (`owner/name`), `name`, `description`, `tags`, `subcategory`, `tier`, `added` (`YYYY-MM-DD`), `notes`.
- `description` is one objective English sentence and ends with a period. Describe what the project does. Do not claim it is the best, the fastest, or production-ready unless that is a plain fact.
- `tier` is `main` or `watchlist`. It is a proposal until Rex merges the pull request.
- Tags currently used: `ai`, `open-core`, `non-osi`, `new`, `experimental`.

## What gets listed

`scripts/score.py` scores 0–100. The weights are interest 15, activity 15, contributors 15, issue and pull-request responsiveness 15, security and Scorecard 15, dependents 10, license and docs 10, reputation and age 5. Counts are log-normalized to the 90th percentile inside the same group. Missing data drops out of the average. It is not scored as zero.

Hard gates:

- Archived, missing (HTTP 404), or no push in 24 months: removed.
- Younger than 30 days: rejected.
- 30 to 90 days old, or a license that is not OSI-approved: Watchlist only.
- Main: score at least 70, age at least 90 days, and inside the group cap of about 15.
- Watchlist: score 50–69, or a high score that a gate holds back.
- A later move between Main and Watchlist waits for two consecutive weekly results (72 to move up, under 65 to move down) unless a hard gate trips.

The Main cut-off stays at **70** for v0.1. Recalibration waits until star-growth, Scorecard, and dependents coverage improve. A change to the cut-off is its own pull request for Rex, not a line in a data pull request.

Do not submit cracks, leaked keys, typosquats, or repositories whose README is copied from another project. Out-of-scope work (image generation, drawing apps, and similar) stays out even when the score is high.

## Checks

```bash
pip install -r requirements-dev.txt
python scripts/validate.py
python -m pytest
python scripts/build.py
python scripts/build.py --check
python scripts/score.py --check --metrics data/metrics/2026-11-09.json
```

Collection uses `GITHUB_TOKEN` and is meant to run in GitHub Actions. Do not commit tokens, `.env` files, or anything scraped from a private source.

## License

By contributing you agree that your contribution is released under [CC0-1.0](LICENSE), the same as the rest of this repository.
