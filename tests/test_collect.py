import io
import json
import urllib.error
from datetime import date, datetime, timezone

import pytest
import yaml

from collect import (
    Client,
    GitHubError,
    build_daily_report,
    collect,
    contributor_count,
    fetch_core,
    graphql_query,
    is_bot,
    main,
    median_first_response_hours,
    star_growth,
    top_share,
)
from common import GROUPS


def test_token_stays_on_github():
    seen = []

    def transport(url, _body, headers):
        seen.append((url, headers.get("Authorization")))
        payload = {"data": {"r0": None}, "errors": [{"type": "NOT_FOUND", "path": ["r0"]}]}
        return 200, {}, json.dumps(payload).encode()

    client = Client("secret-token", transport=transport)
    client.public_json("https://api.deps.dev/v3alpha/projects/example")
    client.graphql(graphql_query(["octocat/hello-world"], "2026-08-01T00:00:00Z"))
    hosts = {url.split("/")[2]: auth for url, auth in seen}
    assert hosts["api.deps.dev"] is None
    assert hosts["api.github.com"] == "Bearer secret-token"
    assert "secret-token" not in graphql_query(["octocat/hello-world"], "2026-08-01T00:00:00Z")


def test_missing_token_is_rejected():
    with pytest.raises(GitHubError):
        Client("")


def test_daily_report_shape():
    report = build_daily_report(
        [
            {"input": "acme/gone", "http_status": 404},
            {"input": "acme/old", "full_name": "acme/old", "http_status": 200, "archived": True, "latest_release_tag": "v2"},
            {"input": "acme/renamed", "full_name": "acme/new", "http_status": 200, "days_since_push": 10},
            {"input": "acme/err", "error": "graphql failed"},
        ],
        {"acme/old": {"latest_release_tag": "v1"}},
        "2026-11-09T23:00:00+00:00",
    )
    assert report["archived"][0]["repo"] == "acme/old"
    assert report["missing"][0]["status"] == 404
    assert report["renamed"][0]["canonical"] == "acme/new"
    assert report["new_releases"][0]["tag"] == "v2"
    assert report["errors"][0]["repo"] == "acme/err"
    assert report["mode"] == "daily"


def test_star_growth_waits_for_an_old_snapshot():
    today = date(2026, 11, 9)
    assert star_growth(1000, [(date(2026, 11, 1), 900)], today) is None
    assert star_growth(1000, [(date(2026, 8, 1), 800)], today) == 200
    assert star_growth(700, [(date(2026, 8, 1), 800)], today) == 0


def test_bots_and_response_time_and_contributors():
    assert is_bot("dependabot[bot]")
    assert is_bot(None)
    assert not is_bot("octocat")
    hours = median_first_response_hours(
        [
            {"createdAt": f"2026-01-0{index}T00:00:00Z", "comments": {"nodes": [{"createdAt": f"2026-01-0{index}T12:00:00Z"}]}}
            for index in range(1, 6)
        ]
    )
    assert hours == 12
    assert median_first_response_hours([{"createdAt": "2026-01-01T00:00:00Z", "comments": {"nodes": []}}]) is None
    link = '<https://api.github.com/repos/acme/tool/contributors?per_page=1&page=15>; rel="last"'
    assert contributor_count(link, 1, 1) == 15
    share, active = top_share(
        [
            {"author": {"login": "octocat"}, "weeks": [{"w": int(datetime(2026, 10, 1, tzinfo=timezone.utc).timestamp()), "c": 3}]},
            {"author": {"login": "dependabot[bot]"}, "weeks": [{"w": int(datetime(2026, 10, 1, tzinfo=timezone.utc).timestamp()), "c": 100}]},
        ],
        datetime(2026, 11, 9, tzinfo=timezone.utc),
    )
    assert share == 1.0
    assert active == 1


def test_null_issue_and_comment_nodes_do_not_break_the_median():
    """GraphQL nodes arrays include null for issues the token cannot see."""
    valid = [
        {
            "createdAt": f"2026-01-0{index}T00:00:00Z",
            "comments": {"nodes": [{"createdAt": f"2026-01-0{index}T12:00:00Z"}]},
        }
        for index in range(1, 6)
    ]
    assert median_first_response_hours([None, *valid]) == 12
    only_null_comment = {
        "createdAt": "2026-01-01T00:00:00Z",
        "comments": {"nodes": [None]},
    }
    assert median_first_response_hours([only_null_comment]) is None


def test_null_issue_node_keeps_the_repository(monkeypatch):
    monkeypatch.setattr("collect.time.sleep", lambda _seconds: None)

    def transport(_url, _body, _headers):
        nodes = [None]
        nodes.extend(
            {
                "createdAt": f"2026-01-0{index}T00:00:00Z",
                "comments": {"nodes": [None, {"createdAt": f"2026-01-0{index}T06:00:00Z"}]},
            }
            for index in range(1, 6)
        )
        payload = {"data": {"r0": {"nameWithOwner": "acme/tool", "issues": {"nodes": nodes}}}}
        return 200, {}, json.dumps(payload).encode()

    rows = fetch_core(Client("token", transport=transport), ["acme/tool"], "2026-08-01T00:00:00Z")
    assert rows[0]["http_status"] == 200
    assert "error" not in rows[0]
    assert rows[0]["first_response_hours"] == 6


@pytest.mark.parametrize("status", [502, 504])
def test_transient_http_retries_with_exponential_backoff(monkeypatch, status):
    sleeps = []
    monkeypatch.setattr("collect.time.sleep", lambda seconds: sleeps.append(seconds))
    calls = {"n": 0}

    def transport(_url, _body, _headers):
        calls["n"] += 1
        if calls["n"] < 3:
            return status, {}, b""
        return 200, {}, json.dumps({"data": {"ok": True}}).encode()

    client = Client("token", transport=transport)
    got, _headers, parsed = client.json_request("https://api.github.com/graphql", {"query": "{}"})
    assert got == 200
    assert parsed["data"]["ok"] is True
    assert calls["n"] == 3
    assert sleeps == [1, 2]


def test_transient_http_gives_up_after_five_attempts(monkeypatch):
    monkeypatch.setattr("collect.time.sleep", lambda _seconds: None)
    calls = {"n": 0}

    def transport(_url, _body, _headers):
        calls["n"] += 1
        return 504, {}, b""

    client = Client("token", transport=transport)
    with pytest.raises(GitHubError):
        client.json_request("https://api.github.com/graphql", {"query": "{}"})
    assert calls["n"] == 5


def test_urlerror_is_retried_with_exponential_backoff(monkeypatch):
    sleeps = []
    monkeypatch.setattr("collect.time.sleep", lambda seconds: sleeps.append(seconds))
    calls = {"n": 0}

    def urlopen(_request, timeout=60):
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.URLError("timed out")
        return _Response(200, b'{"ok": true}')

    monkeypatch.setattr("collect.urllib.request.urlopen", urlopen)
    client = Client("token", pause=0)
    status, _headers, parsed = client.json_request("https://api.github.com/graphql", {"query": "{}"})
    assert status == 200
    assert parsed["ok"] is True
    assert calls["n"] == 3
    assert sleeps == [1, 2]


def test_one_bad_repository_node_is_skipped(caplog):
    def transport(_url, _body, _headers):
        payload = {
            "data": {
                "r0": "not-an-object",
                "r1": {"nameWithOwner": "acme/good", "issues": {"nodes": []}},
            }
        }
        return 200, {}, json.dumps(payload).encode()

    with caplog.at_level("ERROR"):
        rows = fetch_core(Client("token", transport=transport), ["acme/bad", "acme/good"], "2026-08-01T00:00:00Z")
    assert rows[0]["input"] == "acme/bad"
    assert rows[0]["error"]
    assert rows[1]["full_name"] == "acme/good"
    assert rows[1]["http_status"] == 200
    assert "acme/bad" in caplog.text


def test_full_mode_skips_one_repo_when_rest_keeps_failing(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr("collect.time.sleep", lambda _seconds: None)
    data = _catalog(tmp_path, ["acme/bad", "acme/good"])

    def transport(url, raw, _headers):
        if url.endswith("/graphql"):
            payload = {
                "data": {
                    "r0": {"nameWithOwner": "acme/bad", "issues": {"nodes": []}},
                    "r1": {"nameWithOwner": "acme/good", "issues": {"nodes": []}},
                }
            }
            return 200, {}, json.dumps(payload).encode()
        if "/repos/acme/bad/" in url:
            return 502, {}, b""
        return 200, {}, b"{}"

    with caplog.at_level("ERROR"):
        metrics, _snapshot = collect(data, "full", "token", today=date(2026, 11, 9), transport=transport)
    by_name = {row["full_name"]: row for row in metrics["repos"]}
    assert by_name["acme/bad"]["error"]
    assert "error" not in by_name["acme/good"]
    assert by_name["acme/good"]["http_status"] == 200
    assert "acme/bad" in caplog.text


def test_main_fails_when_most_repos_error(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setattr("collect.time.sleep", lambda _seconds: None)
    data = _catalog(tmp_path, ["acme/one", "acme/two"])

    def urlopen(request, timeout=60):
        raise urllib.error.HTTPError(request.full_url, 504, "Gateway Timeout", {}, io.BytesIO(b""))

    monkeypatch.setattr("collect.urllib.request.urlopen", urlopen)
    code = main(["--mode", "daily", "--data", str(data), "--report", str(tmp_path / "daily-report.json")])
    assert code == 1


def test_main_succeeds_when_a_single_repo_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setattr("collect.time.sleep", lambda _seconds: None)
    data = _catalog(tmp_path, ["acme/bad", "acme/good"])

    def urlopen(request, timeout=60):
        body = json.loads(request.data.decode()) if request.data else {}
        query = body.get("query") or ""
        # graphql_query emits owner and name as separate literals, not "owner/name".
        if 'name: "good"' in query and 'name: "bad"' not in query:
            payload = {"data": {"r0": {"nameWithOwner": "acme/good", "issues": {"nodes": []}}}}
            return _Response(200, json.dumps(payload).encode())
        raise urllib.error.HTTPError(request.full_url, 504, "Gateway Timeout", {}, io.BytesIO(b""))

    monkeypatch.setattr("collect.urllib.request.urlopen", urlopen)
    code = main(["--mode", "daily", "--data", str(data), "--report", str(tmp_path / "daily-report.json")])
    assert code == 0
    report = json.loads((tmp_path / "daily-report.json").read_text(encoding="utf-8"))
    assert [row["repo"] for row in report["errors"]] == ["acme/bad"]
    assert report["checked"] == 2


class _Response:
    def __init__(self, status, body):
        self.status = status
        self.headers = {}
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _catalog(tmp_path, repos):
    data = tmp_path / "data"
    data.mkdir()
    (data / "snapshots").mkdir()
    items = [
        {
            "repo": repo,
            "name": repo.split("/", 1)[1],
            "description": "Example project.",
            "tags": [],
            "subcategory": "Example",
            "tier": "main",
            "added": "2026-11-09",
            "notes": None,
        }
        for repo in repos
    ]
    for index, group in enumerate(GROUPS):
        document = {
            "category": group["title"],
            "slug": group["slug"],
            "items": items if index == 0 else [],
        }
        (data / group["file"]).write_text(yaml.safe_dump(document), encoding="utf-8")
    (data / "removed.yml").write_text("removed: []\n", encoding="utf-8")
    return data
