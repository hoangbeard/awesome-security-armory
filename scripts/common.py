"""Shared paths, catalogue loading, and small formatters."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
METRICS = DATA / "metrics"
SNAPSHOTS = DATA / "snapshots"

GROUPS = [
    {"slug": "ai-coding-agents", "title": "AI Coding Agents & Harness", "file": "ai-coding-agents.yml"},
    {"slug": "ai-skills", "title": "AI Skills", "file": "ai-skills.yml"},
    {"slug": "llm-agent-frameworks", "title": "LLM, Agent Framework & MCP", "file": "llm-agent-frameworks.yml"},
    {"slug": "ai-security", "title": "AI Security", "file": "ai-security.yml"},
    {"slug": "offensive-security", "title": "Offensive / Red Team", "file": "offensive-security.yml"},
    {"slug": "defensive-security", "title": "Defensive / Blue Team", "file": "defensive-security.yml"},
    {"slug": "cloud-kubernetes-security", "title": "Cloud & Kubernetes Security", "file": "cloud-kubernetes-security.yml"},
    {"slug": "devsecops-appsec", "title": "DevSecOps / AppSec", "file": "devsecops-appsec.yml"},
    {"slug": "software-dev-tools", "title": "Software & Dev Tools", "file": "software-dev-tools.yml"},
]

# SPDX ids treated as OSI when GitHub returns one. Hand-read exceptions live in
# data/license_overrides.yml. CC0-1.0 is included because this list itself uses it;
# it is not a signal that a tool's license was OSI in the v0.1 snapshot (those
# rows already carry license_osi).
OSI_LICENSES = {
    "0BSD",
    "AFL-3.0",
    "AGPL-3.0",
    "AGPL-3.0-only",
    "AGPL-3.0-or-later",
    "Apache-2.0",
    "Artistic-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "BSL-1.0",
    "BlueOak-1.0.0",
    "CC0-1.0",
    "CDDL-1.0",
    "EPL-1.0",
    "EPL-2.0",
    "EUPL-1.2",
    "GPL-2.0",
    "GPL-2.0-only",
    "GPL-2.0-or-later",
    "GPL-3.0",
    "GPL-3.0-only",
    "GPL-3.0-or-later",
    "HPND",
    "ISC",
    "LGPL-2.0",
    "LGPL-2.1",
    "LGPL-2.1-only",
    "LGPL-2.1-or-later",
    "LGPL-3.0",
    "LGPL-3.0-only",
    "LGPL-3.0-or-later",
    "MIT",
    "MIT-0",
    "MPL-1.1",
    "MPL-2.0",
    "MS-PL",
    "NCSA",
    "OSL-3.0",
    "PostgreSQL",
    "UPL-1.0",
    "Unlicense",
    "Zlib",
}

SAIGON = timezone(timedelta(hours=7))
REPO_KEYS = ("repo", "name", "description", "tags", "subcategory", "tier", "added", "notes")


def load_yaml(path: Path):
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def dump_yaml(data, path: Path, header: str = "") -> None:
    class _Dumper(yaml.SafeDumper):
        pass

    _Dumper.add_representer(
        type(None), lambda dumper, _value: dumper.represent_scalar("tag:yaml.org,2002:null", "null")
    )
    body = yaml.dump(data, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=200)
    path.write_text(header + body, encoding="utf-8")


def saigon_today() -> date:
    return datetime.now(SAIGON).date()


def as_of_datetime(day: date) -> datetime:
    """Calendar date used by the v0.1 scorer: midnight UTC of that civil date."""
    return datetime(day.year, day.month, day.day, tzinfo=timezone.utc)


def parse_github_time(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def days_since(as_of: datetime, value: str | None) -> int | None:
    parsed = parse_github_time(value)
    if parsed is None:
        return None
    return (as_of - parsed).days


def format_count(value) -> str | None:
    if value is None:
        return None
    number = int(value)
    if abs(number) < 1000:
        return str(number)
    scaled = number / 1000
    text = f"{scaled:.1f}"
    if text.endswith(".0"):
        text = text[:-2]
    return text + "k"


def format_score(value) -> str | None:
    if value is None:
        return None
    text = f"{float(value):.1f}"
    if text.endswith(".0"):
        text = text[:-2]
    return text


def github_slug(text: str) -> str:
    """ASCII stand-in for github-slugger: drop punctuation, turn each space into a hyphen."""
    kept = []
    for char in text.lower():
        if char.isalnum() or char in " -_":
            kept.append(char)
    return "".join(kept).replace(" ", "-")


def repo_url(full_name: str) -> str:
    return f"https://github.com/{full_name}"


def load_metrics(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_metrics_path(directory: Path = METRICS) -> Path:
    files = sorted(directory.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"no metrics in {directory}")
    return files[-1]


def index_metrics(document: dict) -> dict[str, dict]:
    indexed = {}
    for record in document.get("repos") or []:
        name = (record.get("full_name") or record.get("input") or "").lower()
        if name:
            indexed[name] = record
    return indexed
