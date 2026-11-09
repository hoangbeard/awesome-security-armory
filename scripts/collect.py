"""Fetch GitHub metrics with GITHUB_TOKEN.

Daily mode records archived repos, missing repos, renames, and new releases.
Full mode also collects the signals scripts/score.py reads and writes
data/metrics/YYYY-MM-DD.json plus a star snapshot. Neither mode pushes git
refs. Workflows call scripts/push_weekly.sh, which refuses to update main.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from common import (
    DATA,
    GROUPS,
    OSI_LICENSES,
    as_of_datetime,
    load_yaml,
    saigon_today,
)

USER_AGENT = "awesome-security-armory"
API = "https://api.github.com"
DEPS = "https://api.deps.dev/v3alpha"
SCORECARD = "https://api.securityscorecards.dev/projects/github.com"
BOTS = {
    "copilot",
    "copilot-swe-agent",
    "dependabot",
    "dependabot-preview",
    "github-actions",
    "mergify",
    "pre-commit-ci",
    "renovate",
    "renovate-bot",
}
DEPENDENTS_SYSTEMS = ("PYPI", "NPM", "CARGO", "MAVEN")


class GitHubError(RuntimeError):
    pass


def is_bot(login: str | None) -> bool:
    if not login:
        return True
    lowered = login.lower()
    return lowered.endswith("[bot]") or lowered.endswith("-bot") or lowered in BOTS


def contributor_count(link_header: str | None, page_size: int, body_length: int) -> int:
    if link_header:
        match = re.search(r"""[?&]page=(\d+)[^>]*>;\s*rel="last\"""", link_header)
        if match:
            return int(match.group(1)) * page_size
    return body_length


def top_share(authors: list[dict], as_of: datetime) -> tuple[float | None, int | None]:
    cutoff = int(as_of.timestamp()) - 365 * 86400
    totals: dict[str, int] = {}
    for author in authors:
        login = (author.get("author") or {}).get("login")
        if is_bot(login):
            continue
        commits = sum(week.get("c") or 0 for week in author.get("weeks") or [] if (week.get("w") or 0) >= cutoff)
        if commits and login:
            totals[login] = commits
    if not totals:
        return None, 0
    return round(max(totals.values()) / sum(totals.values()), 3), len(totals)


def median_first_response_hours(nodes: list[dict]) -> float | None:
    hours = []
    for node in nodes:
        comments = ((node.get("comments") or {}).get("nodes")) or []
        if not comments or not node.get("createdAt") or not comments[0].get("createdAt"):
            continue
        created = datetime.fromisoformat(node["createdAt"].replace("Z", "+00:00"))
        replied = datetime.fromisoformat(comments[0]["createdAt"].replace("Z", "+00:00"))
        hours.append((replied - created).total_seconds() / 3600)
    if len(hours) < 5:
        return None
    hours.sort()
    middle = len(hours) // 2
    if len(hours) % 2:
        return hours[middle]
    return (hours[middle - 1] + hours[middle]) / 2


def star_growth(current: int | None, history: list[tuple[date, int | None]], today: date) -> int | None:
    """Stars gained versus a snapshot about 90 days old. None until one is 60 days old."""
    if current is None:
        return None
    target = today - timedelta(days=90)
    best: tuple[date, int] | None = None
    for snap_date, stars in history:
        if stars is None or (today - snap_date).days < 60:
            continue
        if best is None or abs((snap_date - target).days) < abs((best[0] - target).days):
            best = (snap_date, stars)
    if best is None:
        return None
    return max(0, current - best[1])


def build_daily_report(observed: list[dict], previous: dict[str, dict], generated: str) -> dict:
    archived, missing, renamed, releases, stale, errors = [], [], [], [], [], []
    for row in observed:
        repo = row.get("input") or row.get("full_name")
        prior = previous.get((repo or "").lower(), {})
        if row.get("error"):
            errors.append({"repo": repo, "error": row["error"]})
            continue
        status = row.get("http_status", 200)
        if status != 200:
            missing.append({"repo": repo, "status": status})
            continue
        canonical = row.get("full_name")
        if canonical and repo and canonical.lower() != repo.lower():
            renamed.append({"repo": repo, "canonical": canonical})
        if row.get("archived"):
            archived.append({"repo": canonical or repo})
        tag = row.get("latest_release_tag")
        if tag and tag != prior.get("latest_release_tag"):
            releases.append({"repo": canonical or repo, "tag": tag, "published_at": row.get("latest_release_at")})
        push_age = row.get("days_since_push")
        if push_age is not None and push_age > 730:
            stale.append({"repo": canonical or repo, "pushed_at": row.get("pushed_at"), "days": push_age})
    return {
        "generated": generated,
        "timezone": "Asia/Saigon (UTC+7)",
        "mode": "daily",
        "checked": len(observed),
        "archived": archived,
        "missing": missing,
        "renamed": renamed,
        "new_releases": releases,
        "stale_push": stale,
        "errors": errors,
    }


def tracked_repos(data_dir: Path) -> list[dict]:
    rows = []
    for group in GROUPS:
        document = load_yaml(data_dir / group["file"])
        for item in document["items"]:
            rows.append({"repo": item["repo"], "category": group["slug"], "tier": item["tier"]})
    removed = load_yaml(data_dir / "removed.yml")
    for item in removed["removed"]:
        rows.append({"repo": item["repo"], "category": item["category"], "tier": "removed"})
    return rows


def _graphql_repo(alias: str, owner: str, name: str, since: str) -> str:
    owner_lit = json.dumps(owner)
    name_lit = json.dumps(name)
    since_lit = json.dumps(since)
    return f"""
    {alias}: repository(owner: {owner_lit}, name: {name_lit}) {{
      nameWithOwner
      isArchived
      isFork
      stargazerCount
      forkCount
      createdAt
      pushedAt
      description
      homepageUrl
      isSecurityPolicyEnabled
      licenseInfo {{ spdxId }}
      owner {{ __typename }}
      latestRelease {{ publishedAt tagName }}
      releases {{ totalCount }}
      defaultBranchRef {{
        target {{
          ... on Commit {{
            history(since: {since_lit}) {{ totalCount }}
          }}
        }}
      }}
      issues(last: 20, orderBy: {{field: CREATED_AT, direction: DESC}}) {{
        nodes {{ createdAt comments(first: 1) {{ nodes {{ createdAt }} }} }}
      }}
    }}
    """


def graphql_query(repos: list[str], since: str) -> str:
    parts = []
    for index, full_name in enumerate(repos):
        owner, name = full_name.split("/", 1)
        parts.append(_graphql_repo(f"r{index}", owner, name, since))
    return "query {" + "\n".join(parts) + "\n}"


class Client:
    def __init__(self, token: str, transport=None, pause: float | None = None):
        if not token:
            raise GitHubError("GITHUB_TOKEN is required")
        self.token = token
        self.transport = transport
        self.pause = 0.0 if transport is not None else (2.1 if pause is None else pause)

    def _request(self, url: str, payload: dict | None = None, accept: str | None = None) -> tuple[int, dict, bytes]:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": accept or "application/vnd.github+json",
        }
        host = urllib.parse.urlparse(url).hostname or ""
        if host == "api.github.com" or host.endswith(".github.com"):
            headers["Authorization"] = f"Bearer {self.token}"
        data = None if payload is None else json.dumps(payload).encode()
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if self.transport is not None:
            status, response_headers, body = self.transport(url, data, headers)
            return status, response_headers, body
        request = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read()

    def json_request(self, url: str, payload: dict | None = None, retries: int = 5) -> tuple[int, dict, dict]:
        for attempt in range(retries):
            status, headers, body = self._request(url, payload)
            if status == 202 or status in {403, 429, 502, 503}:
                time.sleep(self.pause or min(60, 5 * (attempt + 1)))
                continue
            try:
                parsed = json.loads(body.decode() or "null")
            except json.JSONDecodeError:
                parsed = {}
            return status, headers, parsed if isinstance(parsed, dict) else {"_list": parsed}
        raise GitHubError(f"gave up on {url.split('?', 1)[0]}")

    def public_json(self, url: str) -> dict | None:
        status, _headers, parsed = self.json_request(url)
        if status != 200:
            return None
        return parsed

    def graphql(self, query: str) -> dict:
        status, _headers, parsed = self.json_request(f"{API}/graphql", {"query": query})
        if status != 200:
            raise GitHubError(f"GraphQL HTTP {status}")
        if parsed.get("errors") and not parsed.get("data"):
            raise GitHubError(parsed["errors"][0].get("message", "graphql error"))
        return parsed


def parse_repository(node: dict | None, requested: str, errors: list[dict]) -> dict:
    if node is None:
        missing = any(error.get("type") == "NOT_FOUND" for error in errors)
        return {"input": requested, "full_name": requested, "http_status": 404 if missing else 0, "error": errors or "missing"}
    license_info = node.get("licenseInfo") or {}
    release = node.get("latestRelease") or {}
    history = (((node.get("defaultBranchRef") or {}).get("target") or {}).get("history") or {})
    return {
        "input": requested,
        "full_name": node.get("nameWithOwner") or requested,
        "http_status": 200,
        "archived": node.get("isArchived"),
        "is_fork": node.get("isFork"),
        "stars": node.get("stargazerCount"),
        "forks": node.get("forkCount"),
        "created_at": node.get("createdAt"),
        "pushed_at": node.get("pushedAt"),
        "description_github": node.get("description"),
        "homepage": node.get("homepageUrl") or None,
        "has_security_md": node.get("isSecurityPolicyEnabled"),
        "license": license_info.get("spdxId"),
        "license_github": license_info.get("spdxId"),
        "is_org": (node.get("owner") or {}).get("__typename") == "Organization",
        "latest_release_at": release.get("publishedAt"),
        "latest_release_tag": release.get("tagName"),
        "release_count": (node.get("releases") or {}).get("totalCount"),
        "commits_90d": history.get("totalCount"),
        "first_response_hours": median_first_response_hours(((node.get("issues") or {}).get("nodes")) or []),
    }


def _apply_license(record: dict, overrides: dict[str, dict]) -> None:
    spdx = record.get("license")
    if spdx in OSI_LICENSES:
        record["license_osi"] = True
        record["license_source"] = "GitHub SPDX"
        return
    override = overrides.get(record["full_name"].lower())
    if override and spdx in {None, "NOASSERTION", "OTHER"}:
        record["license"] = override["resolved"]
        record["license_osi"] = bool(override["osi"])
        record["license_source"] = override.get("note") or "LICENSE file read manually"
        return
    record["license_osi"] = False
    record["license_source"] = "GitHub SPDX"


def load_overrides(data_dir: Path) -> dict[str, dict]:
    path = data_dir / "license_overrides.yml"
    if not path.exists():
        return {}
    document = load_yaml(path) or {}
    return {row["repo"].lower(): row for row in document.get("overrides") or []}


def enrich_rest(client: Client, record: dict, as_of: datetime, full: bool) -> None:
    full_name = record["full_name"]
    if not full:
        return
    status, headers, body = client.json_request(
        f"{API}/repos/{full_name}/contributors?per_page=1&anon=true"
    )
    if status == 200:
        authors = body.get("_list")
        length = len(authors) if isinstance(authors, list) else 0
        link = next((value for key, value in headers.items() if str(key).lower() == "link"), None)
        count = contributor_count(link, 1, length)
        record["contributors"] = None if count == 0 else count
    stats_status, _stats_headers, stats = client.json_request(f"{API}/repos/{full_name}/stats/contributors")
    authors = stats.get("_list") if isinstance(stats.get("_list"), list) else []
    if stats_status == 200:
        share, active = top_share(authors, as_of)
        record["top_contributor_share_12m"] = share
        record["active_contributors_12m_top100"] = active
    community_status, _community_headers, community = client.json_request(
        f"{API}/repos/{full_name}/community/profile"
    )
    if community_status == 200:
        files = community.get("files") or {}
        overview = [
            name
            for key, name in (
                ("readme", "readme"),
                ("contributing", "contributing"),
                ("code_of_conduct", "code_of_conduct"),
                ("license", "license"),
                ("security", "security"),
            )
            if files.get(key)
        ]
        record["overview_files"] = overview
        if files.get("security"):
            record["has_security_md"] = True
    scorecard = client.public_json(f"{SCORECARD}/{full_name}")
    if scorecard and "score" in scorecard:
        record["scorecard_score"] = scorecard.get("score")
        record["scorecard_date"] = scorecard.get("date")
        record["scorecard_checks"] = {check.get("name"): check.get("score") for check in scorecard.get("checks") or []}
    else:
        record["scorecard_score"] = None
        record["scorecard_checks"] = None
    record["dependents_repos"] = package_dependents(client, full_name)
    record["issues_sample"], record["issues_closed"] = search_pair(
        client, full_name, "is:issue", as_of
    )
    record["prs_sample"], record["prs_merged"] = search_pair(client, full_name, "is:pr", as_of, merged=True)


def search_pair(client: Client, full_name: str, kind: str, as_of: datetime, merged: bool = False) -> tuple[int | None, int | None]:
    end = (as_of.date() - timedelta(days=30)).isoformat()
    start = (as_of.date() - timedelta(days=90)).isoformat()
    window = f"created:{start}..{end}"
    total = search_count(client, f"repo:{full_name} {kind} {window}")
    if merged:
        closed = search_count(client, f"repo:{full_name} is:pr is:merged {window}")
    else:
        closed = search_count(client, f"repo:{full_name} is:issue is:closed {window}")
    return total, closed


def search_count(client: Client, query: str) -> int | None:
    if client.pause:
        time.sleep(client.pause)
    quoted = urllib.parse.quote(query)
    status, _headers, body = client.json_request(f"{API}/search/issues?q={quoted}&per_page=1")
    if status != 200:
        return None
    return body.get("total_count")


def package_dependents(client: Client, full_name: str) -> int | None:
    project = urllib.parse.quote(f"github.com/{full_name}", safe="")
    listing = client.public_json(f"{DEPS}/projects/{project}:packageversions")
    if not listing:
        return None
    chosen = None
    for system in DEPENDENTS_SYSTEMS:
        for version in listing.get("versions") or []:
            key = version.get("versionKey") or {}
            if key.get("system") == system:
                chosen = key
                break
        if chosen:
            break
    if not chosen:
        return None
    package = urllib.parse.quote(chosen["name"], safe="")
    details = client.public_json(f"{DEPS}/systems/{chosen['system']}/packages/{package}")
    version = chosen.get("version")
    for entry in (details or {}).get("versions") or []:
        if entry.get("isDefault"):
            version = (entry.get("versionKey") or {}).get("version") or version
            break
    if not version:
        return None
    encoded_version = urllib.parse.quote(version, safe="")
    dependents = client.public_json(
        f"{DEPS}/systems/{chosen['system']}/packages/{package}/versions/{encoded_version}:dependents"
    )
    if not dependents or "dependentCount" not in dependents:
        return None
    return dependents["dependentCount"]


def fetch_core(client: Client, repos: list[str], since: str) -> list[dict]:
    if not repos:
        return []
    try:
        payload = client.graphql(graphql_query(repos, since))
    except GitHubError:
        if len(repos) == 1:
            return [{"input": repos[0], "full_name": repos[0], "http_status": 0, "error": "graphql failed"}]
        middle = max(1, len(repos) // 2)
        return fetch_core(client, repos[:middle], since) + fetch_core(client, repos[middle:], since)
    data = payload.get("data") or {}
    errors = payload.get("errors") or []
    rows = []
    for index, repo in enumerate(repos):
        alias = f"r{index}"
        related = [error for error in errors if error.get("path", [None])[0] == alias]
        rows.append(parse_repository(data.get(alias), repo, related))
    return rows


def load_snapshot_history(directory: Path) -> dict[str, list[tuple[date, int | None]]]:
    history: dict[str, list[tuple[date, int | None]]] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            snap_date = date.fromisoformat(path.stem)
        except ValueError:
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        for name, row in (document.get("repos") or {}).items():
            stars = row.get("stars") if isinstance(row, dict) else None
            history.setdefault(name.lower(), []).append((snap_date, stars))
    return history


def collect(data_dir: Path, mode: str, token: str, today: date | None = None, transport=None) -> tuple[dict, dict | None]:
    today = today or saigon_today()
    as_of = as_of_datetime(today)
    since = (as_of - timedelta(days=90)).isoformat().replace("+00:00", "Z")
    client = Client(token, transport=transport)
    catalog = tracked_repos(data_dir)
    overrides = load_overrides(data_dir)
    growth_history = load_snapshot_history(data_dir / "snapshots")
    core = fetch_core(client, [row["repo"] for row in catalog], since)
    by_input = {row["input"].lower(): row for row in core}
    observed = []
    for row in catalog:
        record = dict(by_input.get(row["repo"].lower()) or {"input": row["repo"], "full_name": row["repo"], "http_status": 0})
        record["category"] = row["category"]
        record["catalog_tier"] = row["tier"]
        if record.get("http_status") == 200:
            _apply_license(record, overrides)
            record["days_since_push"] = None
            pushed = record.get("pushed_at")
            if pushed:
                pushed_at = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
                record["days_since_push"] = (as_of - pushed_at).days
            if mode == "full":
                enrich_rest(client, record, as_of, full=True)
                record["star_growth_90d"] = star_growth(
                    record.get("stars"), growth_history.get(record["full_name"].lower(), []), today
                )
        observed.append(record)
    generated = datetime.now(timezone.utc).isoformat()
    if mode == "daily":
        previous_path = _latest(data_dir / "metrics")
        previous = {}
        if previous_path:
            previous = {
                (row.get("full_name") or "").lower(): row
                for row in json.loads(previous_path.read_text(encoding="utf-8")).get("repos") or []
            }
        return build_daily_report(observed, previous, generated), None
    metrics = {
        "generated": today.isoformat(),
        "timezone": "Asia/Saigon (UTC+7)",
        "source": "github-api",
        "repos": observed,
    }
    snapshot = {
        "date": today.isoformat(),
        "timezone": "Asia/Saigon (UTC+7)",
        "repos": {
            row["full_name"]: {
                "stars": row.get("stars"),
                "forks": row.get("forks"),
                "pushed_at": row.get("pushed_at"),
                "archived": row.get("archived"),
            }
            for row in observed
            if row.get("http_status") == 200 and row.get("full_name")
        },
    }
    return metrics, snapshot


def _latest(directory: Path) -> Path | None:
    files = sorted(directory.glob("*.json"))
    return files[-1] if files else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect GitHub metrics into data/")
    parser.add_argument("--mode", choices=("daily", "full"), default="daily")
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--report", type=Path, help="Where to write daily-report.json")
    args = parser.parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    try:
        first, second = collect(args.data, args.mode, token)
    except GitHubError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.mode == "daily":
        destination = args.report or Path("daily-report.json")
        destination.write_text(json.dumps(first, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {destination}")
        return 0
    metrics_dir = args.data / "metrics"
    snapshot_dir = args.data / "snapshots"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    day = first["generated"]
    metrics_path = metrics_dir / f"{day}.json"
    snapshot_path = snapshot_dir / f"{day}.json"
    metrics_path.write_text(json.dumps(first, indent=2) + "\n", encoding="utf-8")
    snapshot_path.write_text(json.dumps(second, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {metrics_path} and {snapshot_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
