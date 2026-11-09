from pathlib import Path

import yaml

from validate import validate_data

ROOT = Path(__file__).resolve().parents[1]


def test_real_catalogue_is_valid():
    assert validate_data(ROOT / "data") == []


def test_duplicate_and_bad_tier_fail(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "schema").mkdir()
    source = ROOT / "data"
    for path in source.glob("*.yml"):
        (data / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    (data / "schema" / "catalog.schema.json").write_text(
        (source / "schema" / "catalog.schema.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    document = yaml.safe_load((data / "ai-security.yml").read_text(encoding="utf-8"))
    document["items"][0]["tier"] = "core"
    document["items"][1]["repo"] = document["items"][0]["repo"]
    (data / "ai-security.yml").write_text(yaml.safe_dump(document), encoding="utf-8")
    errors = validate_data(data)
    assert any("tier" in error for error in errors)
    assert any("duplicate" in error for error in errors)


def test_v01_counts():
    counts = {}
    for name in (
        "ai-coding-agents.yml",
        "llm-agent-frameworks.yml",
        "ai-security.yml",
        "offensive-security.yml",
        "defensive-security.yml",
        "cloud-kubernetes-security.yml",
        "devsecops-appsec.yml",
        "software-dev-tools.yml",
    ):
        document = yaml.safe_load((ROOT / "data" / name).read_text(encoding="utf-8"))
        counts[name] = {
            "main": sum(item["tier"] == "main" for item in document["items"]),
            "watchlist": sum(item["tier"] == "watchlist" for item in document["items"]),
        }
    assert counts["ai-coding-agents.yml"] == {"main": 8, "watchlist": 9}
    assert counts["llm-agent-frameworks.yml"] == {"main": 13, "watchlist": 2}
    assert counts["ai-security.yml"] == {"main": 10, "watchlist": 4}
    assert counts["offensive-security.yml"] == {"main": 12, "watchlist": 4}
    assert counts["defensive-security.yml"] == {"main": 12, "watchlist": 3}
    assert counts["cloud-kubernetes-security.yml"] == {"main": 10, "watchlist": 4}
    assert counts["devsecops-appsec.yml"] == {"main": 15, "watchlist": 1}
    assert counts["software-dev-tools.yml"] == {"main": 9, "watchlist": 5}
    removed = yaml.safe_load((ROOT / "data" / "removed.yml").read_text(encoding="utf-8"))
    assert len(removed["removed"]) == 11
    listed = sum(value["main"] + value["watchlist"] for value in counts.values())
    assert listed == 121
