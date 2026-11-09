"""Validate catalogue YAML against the v0.1 schema. No third-party schema library."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from common import DATA, GROUPS, REPO_KEYS, load_yaml

REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLUGS = {group["slug"] for group in GROUPS}


def _date(value: str) -> bool:
    if not isinstance(value, str) or not DATE_RE.match(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def validate_data(data_dir: Path = DATA) -> list[str]:
    errors: list[str] = []
    seen: dict[str, str] = {}

    def take(repo: str, where: str) -> None:
        if not isinstance(repo, str) or not REPO_RE.match(repo):
            errors.append(f"{where}: repo must look like owner/name")
            return
        key = repo.lower()
        if key in seen:
            errors.append(f"{where}: duplicate repo {repo} (also in {seen[key]})")
        else:
            seen[key] = where

    for group in GROUPS:
        path = data_dir / group["file"]
        if not path.exists():
            errors.append(f"missing {path.name}")
            continue
        document = load_yaml(path) or {}
        if document.get("category") != group["title"]:
            errors.append(f"{path.name}: category {document.get('category')!r} != {group['title']!r}")
        if document.get("slug") != group["slug"]:
            errors.append(f"{path.name}: slug {document.get('slug')!r}")
        items = document.get("items")
        if not isinstance(items, list):
            errors.append(f"{path.name}: items must be a list")
            continue
        for index, item in enumerate(items, start=1):
            where = f"{path.name}#{index}"
            if not isinstance(item, dict):
                errors.append(f"{where}: item must be a mapping")
                continue
            extra = set(item) - set(REPO_KEYS)
            missing = [key for key in REPO_KEYS if key not in item]
            if extra:
                errors.append(f"{where}: unexpected fields {sorted(extra)}")
            if missing:
                errors.append(f"{where}: missing {missing}")
            take(item.get("repo", ""), where)
            if not isinstance(item.get("name"), str) or not item.get("name"):
                errors.append(f"{where}: name is required")
            description = item.get("description")
            if not isinstance(description, str) or not description.strip():
                errors.append(f"{where}: description is required")
            elif not description.rstrip().endswith((".", "!", "?")):
                errors.append(f"{where}: description must end with punctuation")
            tags = item.get("tags")
            if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
                errors.append(f"{where}: tags must be a list of strings")
            if item.get("tier") not in {"main", "watchlist"}:
                errors.append(f"{where}: tier must be main or watchlist")
            if not _date(str(item.get("added"))):
                errors.append(f"{where}: added must be YYYY-MM-DD")
            notes = item.get("notes")
            if notes is not None and not isinstance(notes, str):
                errors.append(f"{where}: notes must be a string or null")

    removed_path = data_dir / "removed.yml"
    removed = load_yaml(removed_path) if removed_path.exists() else None
    rows = (removed or {}).get("removed") if isinstance(removed, dict) else None
    if not isinstance(rows, list):
        errors.append("removed.yml: removed must be a list")
    else:
        for index, row in enumerate(rows, start=1):
            where = f"removed.yml#{index}"
            for key in ("repo", "category", "removed", "reason", "source"):
                if key not in row:
                    errors.append(f"{where}: missing {key}")
            take(row.get("repo", ""), where)
            if row.get("category") not in SLUGS:
                errors.append(f"{where}: unknown category {row.get('category')!r}")
            if not _date(str(row.get("removed"))):
                errors.append(f"{where}: removed date is invalid")
            if not isinstance(row.get("reason"), str) or not row.get("reason"):
                errors.append(f"{where}: reason is required")

    candidates_path = data_dir / "candidates.yml"
    candidates = load_yaml(candidates_path) if candidates_path.exists() else None
    if not isinstance(candidates, dict) or not isinstance(candidates.get("candidates"), list):
        errors.append("candidates.yml: candidates must be a list")

    schema = data_dir / "schema" / "catalog.schema.json"
    if not schema.exists():
        errors.append("missing data/schema/catalog.schema.json")
    else:
        try:
            json.loads(schema.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"catalog.schema.json: {exc}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate data/*.yml")
    parser.add_argument("--data", type=Path, default=DATA)
    args = parser.parse_args(argv)
    errors = validate_data(args.data)
    if errors:
        print("\n".join(errors))
        return 1
    print("catalogue ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
