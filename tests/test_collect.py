import json
from datetime import date, datetime, timezone

import pytest

from collect import (
    Client,
    GitHubError,
    build_daily_report,
    contributor_count,
    graphql_query,
    is_bot,
    median_first_response_hours,
    star_growth,
    top_share,
)


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
