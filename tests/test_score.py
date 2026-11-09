from datetime import datetime, timezone

from common import as_of_datetime, load_yaml
from score import (
    ADMIT_SCORE,
    MAIN_CAP,
    anomaly_reasons,
    annotate,
    catalog_state,
    combine,
    component_scores,
    decide_group,
    log_norm,
    p90,
    rescore_file,
    score_records,
    thresholds_for,
)

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
AS_OF = as_of_datetime(__import__("datetime").date(2026, 11, 9))


def _repo(**overrides):
    base = {
        "full_name": "acme/tool",
        "category": "ai-security",
        "http_status": 200,
        "archived": False,
        "created_at": "2024-01-01T00:00:00Z",
        "pushed_at": "2026-11-01T00:00:00Z",
        "stars": 1000,
        "forks": 100,
        "commits_90d": 50,
        "contributors": 20,
        "top_contributor_share_12m": 0.4,
        "latest_release_at": "2026-10-01T00:00:00Z",
        "release_count": 3,
        "has_security_md": True,
        "overview_files": ["readme", "contributing"],
        "homepage": "https://example.com",
        "license_osi": True,
        "is_org": True,
        "issues_sample": 10,
        "issues_closed": 8,
        "prs_sample": 10,
        "prs_merged": 7,
        "dependents_repos": 20,
    }
    base.update(overrides)
    return base


def test_snapshot_scores_match():
    mismatches = rescore_file(ROOT / "data" / "metrics" / "2026-11-09.json")
    assert mismatches == []


def test_missing_weight_is_not_treated_as_zero():
    present = _repo()
    missing = _repo(scorecard_score=None)
    zero = _repo(scorecard_score=0)
    threshold = thresholds_for([present])
    present_score, present_weight = combine(component_scores(present, threshold, AS_OF), True)
    missing_score, missing_weight = combine(component_scores(missing, threshold, AS_OF), True)
    zero_score, zero_weight = combine(component_scores(zero, threshold, AS_OF), True)
    assert present_weight == missing_weight
    assert zero_weight == present_weight + 9
    assert zero_score < missing_score
    assert present_score == missing_score


def test_log_norm_uses_group_ceiling():
    assert round(p90([1, 2, 3, 4, 100]), 1) == 61.6
    assert log_norm(100, 100) == 1
    assert log_norm(None, 100) is None
    assert log_norm(0, 100) < 0.01


def test_dead_and_young_repos_are_rejected():
    dead = score_records([_repo(full_name="acme/old", archived=True)], AS_OF)[0]
    missing = score_records([_repo(full_name="acme/gone", http_status=404)], AS_OF)[0]
    stale = score_records([_repo(full_name="acme/stale", pushed_at="2020-01-01T00:00:00Z")], AS_OF)[0]
    baby = score_records([_repo(full_name="acme/new", created_at="2026-11-01T00:00:00Z")], AS_OF)[0]
    records = [dead, missing, stale, baby]
    decisions = decide_group(records, {}, {}, {}, {}, {}, AS_OF)
    assert decisions["acme/old"]["tier"] == "removed"
    assert "archived" in decisions["acme/old"]["reasons"][0]
    assert decisions["acme/gone"]["tier"] == "removed"
    assert decisions["acme/stale"]["tier"] == "removed"
    assert decisions["acme/new"]["tier"] == "removed"
    flaky = score_records([_repo(full_name="acme/flaky", http_status=0)], AS_OF)[0]
    held = decide_group([flaky], {"acme/flaky": "main"}, {}, {}, {}, {}, AS_OF)
    assert held["acme/flaky"]["tier"] == "main"


def test_non_osi_and_mid_age_stay_on_watchlist():
    records = score_records(
        [
            _repo(full_name="acme/proprietary", license_osi=False, stars=5000),
            _repo(full_name="acme/young", created_at="2026-09-01T00:00:00Z", stars=5000),
        ],
        AS_OF,
    )
    decisions = decide_group(records, {}, {}, {}, {}, {}, AS_OF)
    assert decisions["acme/proprietary"]["tier"] == "watchlist"
    assert decisions["acme/young"]["tier"] == "watchlist"
    assert any("OSI" in reason for reason in decisions["acme/proprietary"]["reasons"])


def test_new_repo_bands_and_main_cap():
    records = []
    for index in range(MAIN_CAP + 1):
        records.append(_repo(full_name=f"acme/tool-{index}", stars=1000 + index, category="demo"))
    records.append(_repo(full_name="acme/mid", stars=10, commits_90d=1, contributors=1, dependents_repos=0))
    scored = score_records(records, AS_OF)
    by_name = {row["full_name"]: row["score"] for row in scored}
    assert by_name["acme/tool-15"] >= 70
    decisions = decide_group(scored, {}, {}, {}, {}, {}, AS_OF)
    mains = [name for name, decision in decisions.items() if decision["tier"] == "main"]
    assert len(mains) == MAIN_CAP
    capped = [name for name, decision in decisions.items() if any("cap" in reason for reason in decision["reasons"])]
    assert capped
    assert all(decisions[name]["tier"] == "watchlist" for name in capped)


def test_buffer_blocks_a_single_week_move():
    record = score_records([_repo(stars=5000)], AS_OF)[0]
    assert record["score"] >= 72
    stay = decide_group([record], {"acme/tool": "watchlist"}, {}, {}, {}, {}, AS_OF)
    assert stay["acme/tool"]["tier"] == "watchlist"
    promote = decide_group([record], {"acme/tool": "watchlist"}, {"acme/tool": [80]}, {}, {}, {}, AS_OF)
    assert promote["acme/tool"]["tier"] == "main"
    weak = score_records([_repo(stars=1, forks=0, commits_90d=0, contributors=1, dependents_repos=0, has_security_md=False, license_osi=True, homepage=None, overview_files=[], release_count=0, latest_release_at=None, issues_sample=0, prs_sample=0, is_org=False)], AS_OF)[0]
    # Force the numeric band the buffer cares about.
    weak["score"] = 60
    held = decide_group([weak], {"acme/tool": "main"}, {}, {}, {}, {}, AS_OF)
    assert held["acme/tool"]["tier"] == "main"
    demoted = decide_group([weak], {"acme/tool": "main"}, {"acme/tool": [60]}, {}, {}, {}, AS_OF)
    assert demoted["acme/tool"]["tier"] == "watchlist"


def test_watchlist_removal_needs_four_weeks_unless_an_exception_applies():
    record = score_records([_repo()], AS_OF)[0]
    record["score"] = 40
    removed = decide_group(
        [record],
        {"acme/tool": "watchlist"},
        {"acme/tool": [40, 40, 40]},
        {"acme/tool": "2026-11-01"},
        {},
        {},
        AS_OF,
    )
    assert removed["acme/tool"]["tier"] == "removed"
    osi = score_records([_repo(license_osi=False)], AS_OF)[0]
    osi["score"] = 40
    kept = decide_group(
        [osi],
        {"acme/tool": "watchlist"},
        {"acme/tool": [40, 40, 40]},
        {"acme/tool": "2026-11-01"},
        {},
        {},
        AS_OF,
    )
    assert kept["acme/tool"]["tier"] == "watchlist"


def test_manual_watch_is_not_promoted():
    record = score_records([_repo(full_name="xai-org/grok-build", stars=27000)], AS_OF)[0]
    decision = decide_group(
        [record],
        {"xai-org/grok-build": "watchlist"},
        {"xai-org/grok-build": [90]},
        {},
        {"xai-org/grok-build": "manual anomaly"},
        {},
        AS_OF,
    )
    assert decision["xai-org/grok-build"]["tier"] == "watchlist"


def test_v01_tiers_do_not_move_without_history():
    from score import load_metrics

    document = load_metrics(ROOT / "data" / "metrics" / "2026-11-09.json")
    scored = score_records(document["repos"], AS_OF)
    current, added, _groups = catalog_state(ROOT / "data")
    watch, remove = __import__("score").load_manual(ROOT / "data" / "manual.yml")
    grouped = {}
    for record in scored:
        grouped.setdefault(record["category"], []).append(record)
    moves = []
    for records in grouped.values():
        decisions = decide_group(records, current, {}, added, watch, remove, AS_OF)
        for name, decision in decisions.items():
            if current.get(name) != decision["tier"]:
                moves.append((name, current.get(name), decision))
    assert moves == []


def test_anomaly_rules():
    fast = _repo(stars=100_000, created_at="2026-10-01T00:00:00Z")
    fast["age_days"] = 30
    reasons = anomaly_reasons(fast)
    assert any("star velocity" in reason for reason in reasons)
    burst = _repo(commits_90d=6000, contributors=10)
    burst["age_days"] = 400
    assert any("commits" in reason for reason in anomaly_reasons(burst))


def test_annotate_does_not_rewrite_matching_snapshot(tmp_path):
    source = ROOT / "data" / "metrics" / "2026-11-09.json"
    target = tmp_path / "2026-11-09.json"
    target.write_bytes(source.read_bytes())
    data = tmp_path / "data"
    # annotate compares tiers against the real catalogue; point it at a copy of data via the real tree
    # and a throwaway metrics file so the snapshot bytes stay put when scores already match.
    before = target.read_bytes()
    changes = annotate(target, ROOT / "data", apply=False)
    assert changes == []
    assert target.read_bytes() == before
    assert load_yaml(ROOT / "data" / "ai-coding-agents.yml")["items"][0]["tier"] == "main"
    assert ADMIT_SCORE == 50
