"""Score repositories with the v0.1 rubric and apply tier gates.

Counts are log-normalized to the 90th percentile inside each group. A missing
metric is left out and its weight is spread across the metrics that exist. It
is never stored as zero. Hard gates still remove or cap a repo regardless of
the numeric score. Tier changes that are only about the score wait for a run
of weekly results so one noisy week cannot bounce a project between Main and
Watchlist.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

from common import (
    DATA,
    GROUPS,
    OSI_LICENSES,
    as_of_datetime,
    days_since,
    load_metrics,
    load_yaml,
    saigon_today,
)

WEIGHTS = [
    ("stars", 8),
    ("forks", 3),
    ("star_growth_90d", 4),
    ("commits_90d", 7),
    ("release_12m", 4),
    ("push_recency", 4),
    ("contributors", 7),
    ("top_share", 5),
    ("orgs", 3),
    ("first_response", 5),
    ("issue_close_ratio", 5),
    ("pr_merge_ratio", 5),
    ("scorecard", 9),
    ("security_policy", 3),
    ("signed_releases", 3),
    ("dependents", 7),
    ("notable_users", 3),
    ("osi_license", 5),
    ("docs", 5),
    ("vendor", 3),
    ("age", 2),
]

MAIN_CUTOFF = 70
PROMOTE_SCORE = 72
DEMOTE_SCORE = 65
ADMIT_SCORE = 50
REMOVE_SCORE = 45
MAIN_CAP = 15
MIN_AGE_DAYS = 30
MAIN_AGE_DAYS = 90
STALE_PUSH_DAYS = 730
WATCHLIST_LIMIT_DAYS = 183

COUNT_KEYS = ("stars", "forks", "commits_90d", "contributors", "dependents_repos", "star_growth_90d")


def p90(values) -> float | None:
    usable = sorted(value for value in values if value is not None)
    if not usable:
        return None
    position = 0.9 * (len(usable) - 1)
    lower = math.floor(position)
    upper = min(lower + 1, len(usable) - 1)
    return usable[lower] + (usable[upper] - usable[lower]) * (position - lower)


def log_norm(value, threshold) -> float | None:
    if value is None or threshold is None:
        return None
    ceiling = max(value, threshold)
    if ceiling <= 0:
        return 0.0
    return math.log1p(value) / math.log1p(ceiling)


def response_score(hours) -> float | None:
    """Full credit at or under 24 hours, none at 30 days, linear between."""
    if hours is None:
        return None
    if hours <= 24:
        return 1.0
    if hours >= 24 * 30:
        return 0.0
    return 1 - (hours - 24) / (24 * 30 - 24)


def prepare(record: dict) -> dict:
    prepared = dict(record)
    if prepared.get("contributors") == 0:
        prepared["contributors"] = None
    return prepared


def thresholds_for(records: list[dict]) -> dict:
    live = [record for record in records if record.get("http_status", 200) == 200]
    return {key: p90([record.get(key) for record in live]) for key in COUNT_KEYS}


def component_scores(record: dict, threshold: dict, as_of: datetime) -> dict:
    checks = record.get("scorecard_checks") or {}
    scores = {
        "stars": log_norm(record.get("stars"), threshold.get("stars")),
        "forks": log_norm(record.get("forks"), threshold.get("forks")),
        "star_growth_90d": log_norm(record.get("star_growth_90d"), threshold.get("star_growth_90d")),
        "commits_90d": log_norm(record.get("commits_90d"), threshold.get("commits_90d")),
    }
    release_age = days_since(as_of, record.get("latest_release_at"))
    if record.get("release_count") is not None or release_age is not None:
        scores["release_12m"] = 1.0 if release_age is not None and release_age <= 365 else 0.0
    else:
        scores["release_12m"] = None
    push_age = days_since(as_of, record.get("pushed_at"))
    if push_age is None:
        scores["push_recency"] = None
    elif push_age <= 30:
        scores["push_recency"] = 1.0
    else:
        scores["push_recency"] = max(0.0, 1 - (push_age - 30) / 335)
    scores["contributors"] = log_norm(record.get("contributors"), threshold.get("contributors"))
    top_share = record.get("top_contributor_share_12m")
    if top_share is None:
        scores["top_share"] = None
    elif top_share <= 0.5:
        scores["top_share"] = 1.0
    elif top_share >= 0.8:
        scores["top_share"] = 0.0
    else:
        scores["top_share"] = (0.8 - top_share) / 0.3
    org_signal = checks.get("Contributors")
    scores["orgs"] = None if org_signal is None or org_signal < 0 else org_signal / 10
    scores["first_response"] = response_score(record.get("first_response_hours"))
    issue_sample = record.get("issues_sample") or 0
    scores["issue_close_ratio"] = (
        record["issues_closed"] / issue_sample if issue_sample >= 5 else None
    )
    pull_sample = record.get("prs_sample") or 0
    scores["pr_merge_ratio"] = record["prs_merged"] / pull_sample if pull_sample >= 5 else None
    scorecard = record.get("scorecard_score")
    scores["scorecard"] = None if scorecard is None else scorecard / 10
    security = record.get("has_security_md")
    scores["security_policy"] = None if security is None else (1.0 if security else 0.0)
    signed = checks.get("Signed-Releases")
    scores["signed_releases"] = None if signed is None or signed < 0 else signed / 10
    dependents = record.get("dependents_repos")
    scores["dependents"] = log_norm(dependents, threshold.get("dependents_repos")) if dependents else None
    scores["notable_users"] = record.get("notable_users_score")
    if record.get("license_osi") is not None:
        scores["osi_license"] = 1.0 if record["license_osi"] else 0.0
    else:
        scores["osi_license"] = 1.0 if record.get("license") in OSI_LICENSES else 0.0
    overview = record.get("overview_files")
    if overview is None:
        scores["docs"] = None
    else:
        present = set(overview)
        scores["docs"] = (
            ("readme" in present)
            + ("contributing" in present)
            + ("code_of_conduct" in present)
            + bool(record.get("homepage"))
            + ((record.get("release_count") or 0) > 0)
        ) / 5
    is_org = record.get("is_org")
    scores["vendor"] = None if is_org is None else (1.0 if is_org else 0.0)
    age_days = days_since(as_of, record.get("created_at"))
    scores["age"] = None if age_days is None else min(age_days / 365, 1.0)
    return scores


def combine(components: dict, live: bool) -> tuple[float | None, int]:
    available = [(name, weight) for name, weight in WEIGHTS if components[name] is not None]
    total_weight = sum(weight for _, weight in available)
    if not total_weight or not live:
        return None, total_weight
    raw = 100 * sum(weight * components[name] for name, weight in available) / total_weight
    return round(raw, 1), total_weight


def score_records(records: list[dict], as_of: datetime) -> list[dict]:
    prepared = [prepare(record) for record in records]
    by_category: dict[str, list[dict]] = {}
    for record in prepared:
        by_category.setdefault(record.get("category") or "ungrouped", []).append(record)
    thresholds = {category: thresholds_for(group) for category, group in by_category.items()}
    scored = []
    for record in prepared:
        parts = component_scores(record, thresholds[record.get("category") or "ungrouped"], as_of)
        live = record.get("http_status", 200) == 200
        score, weight = combine(parts, live)
        enriched = dict(record)
        enriched["score_components"] = {
            name: None if parts[name] is None else round(parts[name], 3) for name, _weight in WEIGHTS
        }
        enriched["weight_available"] = weight
        enriched["score"] = score
        enriched["age_days"] = days_since(as_of, record.get("created_at"))
        enriched["days_since_push"] = days_since(as_of, record.get("pushed_at"))
        scored.append(enriched)
    return scored


def anomaly_reasons(record: dict) -> list[str]:
    reasons = []
    stars = record.get("stars") or 0
    age = record.get("age_days") or 0
    if age > 0 and stars / age >= 1000:
        reasons.append(f"anomaly: star velocity {stars / age:.0f} stars/day since creation")
    commits = record.get("commits_90d") or 0
    contributors = record.get("contributors")
    if commits >= 5000 and contributors and commits / contributors >= 5:
        reasons.append(
            f"anomaly: {commits} commits in 90 days ({commits / contributors:.1f} per contributor), "
            "likely automated/agent commits"
        )
    return reasons


def hard_removal(record: dict, manual_remove: str | None) -> str | None:
    status = record.get("http_status", 200)
    # 404 is gone. Other non-200 codes are fetch failures and must not drop a listing.
    if status == 404:
        return "HTTP 404 (not found)"
    if status != 200:
        return None
    if record.get("archived"):
        return "archived"
    push_age = record.get("days_since_push")
    if push_age is not None and push_age > STALE_PUSH_DAYS:
        return "no push in 24 months"
    age = record.get("age_days")
    if age is not None and age < MIN_AGE_DAYS:
        return "repo younger than 30 days"
    if manual_remove:
        return manual_remove
    return None


def watch_caps(record: dict, manual_watch: str | None) -> list[str]:
    reasons = []
    if record.get("license_osi") is False:
        reasons.append("no OSI license (⚠️)")
    age = record.get("age_days")
    if age is not None and age < MAIN_AGE_DAYS:
        reasons.append("younger than 90 days")
    reasons.extend(anomaly_reasons(record))
    if manual_watch:
        reasons.append(manual_watch)
    return reasons


def _consecutive(scores: list[float], predicate, needed: int) -> bool:
    if len(scores) < needed:
        return False
    return all(predicate(score) for score in scores[-needed:])


def decide_group(
    records: list[dict],
    current: dict[str, str | None],
    history: dict[str, list[float]],
    added: dict[str, str | None],
    manual_watch: dict[str, str],
    manual_remove: dict[str, str],
    as_of: datetime,
) -> dict[str, dict]:
    """Return repo -> {tier, reasons}.

    `current` and `history` are keyed by lower-case full name. History does not
    include the score on `record` itself. Repos with no current tier are new
    and are placed immediately. Repos that already have a tier only move on a
    hard gate or after the weekly buffer.
    """
    preliminary = []
    for record in records:
        name = record["full_name"].lower()
        removal = hard_removal(record, manual_remove.get(name))
        caps = watch_caps(record, manual_watch.get(name))
        preliminary.append((record, removal, caps))

    decisions = {}
    for record, removal, caps in preliminary:
        name = record["full_name"].lower()
        score = record.get("score")
        series = list(history.get(name) or [])
        if score is not None:
            series.append(score)
        existing = current.get(name)
        if existing == "removed":
            decisions[name] = {
                "tier": "removed",
                "reasons": ["stays in data/removed.yml until a curator restores it"],
            }
            continue
        if removal:
            decisions[name] = {"tier": "removed", "reasons": [removal]}
            continue
        if existing is None:
            decisions[name] = _place_new(record, caps)
            continue
        decisions[name] = _place_existing(
            record, existing, caps, series, added.get(name), as_of, manual_watch.get(name) is not None
        )
    _apply_main_cap(records, decisions, current)
    return decisions


def _apply_main_cap(records: list[dict], decisions: dict[str, dict], current: dict[str, str | None]) -> None:
    """Keep existing Main rows, then fill up to 15 seats with new promotions."""
    protected = []
    promoted = []
    for record in records:
        name = record["full_name"].lower()
        if decisions[name]["tier"] != "main":
            continue
        if current.get(name) == "main":
            protected.append(record)
        else:
            promoted.append(record)
    slots = max(0, MAIN_CAP - len(protected))
    promoted.sort(key=lambda record: -(record.get("score") or 0))
    for record in promoted[slots:]:
        name = record["full_name"].lower()
        reasons = list(decisions[name]["reasons"])
        reasons.append("category Main cap (15) reached")
        decisions[name] = {"tier": "watchlist", "reasons": reasons}


def _place_new(record: dict, caps: list[str]) -> dict:
    score = record.get("score") or 0
    if score >= MAIN_CUTOFF and not caps:
        return {"tier": "main", "reasons": []}
    if score >= ADMIT_SCORE or (caps and score >= MAIN_CUTOFF):
        return {"tier": "watchlist", "reasons": caps}
    return {"tier": "removed", "reasons": [f"score {record.get('score')} below 50 (not admitted)"]}


def _blocked_from_main(caps: list[str]) -> bool:
    return bool(caps)


def _place_existing(record, existing, caps, series, added_on, as_of, manual: bool) -> dict:
    score = record.get("score")
    # License, age, anomaly, and manual flags move a Main repo immediately.
    if existing == "main" and _blocked_from_main(caps):
        return {"tier": "watchlist", "reasons": caps}
    if existing == "main":
        if _consecutive(series, lambda value: value < DEMOTE_SCORE, 2):
            return {"tier": "watchlist", "reasons": [f"score under {DEMOTE_SCORE} for 2 consecutive weeks"]}
        return {"tier": "main", "reasons": []}
    # Watchlist.
    promotable = (
        not caps
        and score is not None
        and _consecutive(series, lambda value: value >= PROMOTE_SCORE, 2)
    )
    if promotable:
        return {"tier": "main", "reasons": []}
    enduring_exception = manual or any(
        reason.startswith("no OSI") or reason.startswith("anomaly:") for reason in caps
    )
    if not enduring_exception and _consecutive(series, lambda value: value < REMOVE_SCORE, 4):
        return {"tier": "removed", "reasons": [f"score under {REMOVE_SCORE} for 4 consecutive weeks"]}
    if not enduring_exception and added_on and existing == "watchlist":
        added = datetime.fromisoformat(added_on).replace(tzinfo=as_of.tzinfo)
        if as_of - added >= timedelta(days=WATCHLIST_LIMIT_DAYS):
            return {"tier": "removed", "reasons": ["on Watchlist for 6 months without reaching Main"]}
    return {"tier": "watchlist", "reasons": caps}


def rescore_file(path: Path) -> list[str]:
    """Return human-readable mismatches against a scored metrics snapshot."""
    document = load_metrics(path)
    day = datetime.fromisoformat(str(document["generated"])).date()
    scored = score_records(document["repos"], as_of_datetime(day))
    mismatches = []
    for original, fresh in zip(document["repos"], scored):
        if fresh["score"] != original.get("score"):
            mismatches.append(
                f"{original.get('full_name')}: recomputed {fresh['score']} stored {original.get('score')}"
            )
        if fresh["weight_available"] != original.get("weight_available"):
            mismatches.append(
                f"{original.get('full_name')}: weight {fresh['weight_available']} stored {original.get('weight_available')}"
            )
    return mismatches


def load_manual(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    if not path.exists():
        return {}, {}
    document = load_yaml(path) or {}
    watch = {(row["repo"]).lower(): row["reason"] for row in document.get("watch") or []}
    remove = {(row["repo"]).lower(): row["reason"] for row in document.get("remove") or []}
    return watch, remove


def score_history(metrics_dir: Path, exclude: Path) -> dict[str, list[float]]:
    history: dict[str, list[float]] = {}
    for path in sorted(metrics_dir.glob("*.json")):
        if path.resolve() == exclude.resolve():
            continue
        document = load_metrics(path)
        for record in document.get("repos") or []:
            name = (record.get("full_name") or "").lower()
            if name and record.get("score") is not None:
                history.setdefault(name, []).append(record["score"])
    return history


def catalog_state(data_dir: Path) -> tuple[dict[str, str], dict[str, str | None], dict[str, dict]]:
    """current tier, added date, and the parsed group documents keyed by slug."""
    current: dict[str, str] = {}
    added: dict[str, str | None] = {}
    groups = {}
    for group in GROUPS:
        document = load_yaml(data_dir / group["file"])
        groups[group["slug"]] = document
        for item in document["items"]:
            key = item["repo"].lower()
            current[key] = item["tier"]
            added[key] = item.get("added")
    removed = load_yaml(data_dir / "removed.yml")
    for row in removed["removed"]:
        current[row["repo"].lower()] = "removed"
    return current, added, groups


def annotate(metrics_path: Path, data_dir: Path, apply: bool) -> list[str]:
    """Write scores onto a metrics file. With apply, update YAML tiers that actually move."""
    document = load_metrics(metrics_path)
    original_repos = document.get("repos") or []
    day = datetime.fromisoformat(str(document.get("generated") or saigon_today().isoformat())).date()
    as_of = as_of_datetime(day)
    scored = score_records(original_repos, as_of)
    by_name = {row["full_name"].lower(): row for row in scored}
    current, added, _groups = catalog_state(data_dir)
    watch, remove = load_manual(data_dir / "manual.yml")
    history = score_history(metrics_path.parent, metrics_path)
    changes = []
    grouped: dict[str, list[dict]] = {}
    for record in scored:
        grouped.setdefault(record.get("category") or "ungrouped", []).append(record)
    decisions = {}
    for _category, records in grouped.items():
        decisions.update(decide_group(records, current, history, added, watch, remove, as_of))
    for name, decision in sorted(decisions.items()):
        previous = current.get(name)
        if previous is None or previous == decision["tier"]:
            continue
        changes.append(f"{by_name[name]['full_name']}: {previous} -> {decision['tier']} ({'; '.join(decision['reasons'])})")
    scores_differ = len(original_repos) != len(scored) or any(
        before.get("score") != after["score"] or before.get("weight_available") != after["weight_available"]
        for before, after in zip(original_repos, scored)
    )
    if scores_differ:
        document["repos"] = scored
        metrics_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    if apply and changes:
        _write_tier_changes(data_dir, decisions, by_name, as_of)
    return changes


def _write_tier_changes(data_dir: Path, decisions: dict, by_name: dict, as_of: datetime) -> None:
    from common import dump_yaml

    removed_doc = load_yaml(data_dir / "removed.yml")
    removed_rows = list(removed_doc["removed"])
    removed_before = len(removed_rows)
    removed_index = {row["repo"].lower() for row in removed_rows}
    for group in GROUPS:
        path = data_dir / group["file"]
        document = load_yaml(path)
        kept = []
        dirty = False
        for item in document["items"]:
            decision = decisions.get(item["repo"].lower())
            if decision is None or decision["tier"] == item["tier"]:
                kept.append(item)
                continue
            dirty = True
            if decision["tier"] == "removed":
                key = item["repo"].lower()
                if key not in removed_index:
                    record = by_name.get(key, {})
                    removed_rows.append(
                        {
                            "repo": item["repo"],
                            "category": group["slug"],
                            "removed": as_of.date().isoformat(),
                            "last_score": record.get("score"),
                            "reason": "; ".join(decision["reasons"]) or "removed by weekly rescore",
                            "source": "weekly-rescore",
                        }
                    )
                    removed_index.add(key)
                continue
            updated = dict(item)
            updated["tier"] = decision["tier"]
            note = "; ".join(decision["reasons"])
            if note:
                updated["notes"] = note
            kept.append(updated)
        if dirty:
            document["items"] = kept
            header = path.read_text(encoding="utf-8").split("category:", 1)[0]
            dump_yaml(document, path, header if header.startswith("#") else "")
    if len(removed_rows) != removed_before:
        removed_doc["removed"] = removed_rows
        header = (data_dir / "removed.yml").read_text(encoding="utf-8").split("removed:", 1)[0]
        dump_yaml(removed_doc, data_dir / "removed.yml", header if header.startswith("#") else "# Removed by catalogue rules.\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score armory metrics and check the v0.1 snapshot.")
    parser.add_argument("--metrics", type=Path, help="Metrics JSON to rescore")
    parser.add_argument("--check", action="store_true", help="Exit 1 if recomputed scores differ")
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--annotate", action="store_true", help="Write scores back to the metrics file")
    parser.add_argument("--apply", action="store_true", help="With --annotate, update YAML tiers that moved")
    args = parser.parse_args(argv)
    if args.check:
        path = args.metrics or (DATA / "metrics" / "2026-11-09.json")
        mismatches = rescore_file(path)
        if mismatches:
            print("\n".join(mismatches[:20]))
            print(f"{len(mismatches)} mismatches")
            return 1
        print(f"scores match {path.name}")
        return 0
    if args.annotate:
        if args.metrics is None:
            parser.error("--annotate requires --metrics")
        changes = annotate(args.metrics, args.data, apply=args.apply)
        print(f"{len(changes)} tier changes")
        print("\n".join(changes))
        return 0
    if args.metrics:
        document = load_metrics(args.metrics)
        day = datetime.fromisoformat(str(document.get("generated") or saigon_today().isoformat())).date()
        scored = score_records(document["repos"], as_of_datetime(day))
        print(json.dumps({"repos": len(scored), "scored": sum(row["score"] is not None for row in scored)}))
        return 0
    parser.error("pass --check, --annotate, or --metrics")
    return 2


if __name__ == "__main__":
    sys.exit(main())
