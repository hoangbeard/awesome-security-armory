"""Generate README.md from the curated YAML and the latest metrics snapshot."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from common import (
    DATA,
    GROUPS,
    ROOT,
    format_count,
    format_score,
    github_slug,
    index_metrics,
    latest_metrics_path,
    load_metrics,
    load_yaml,
    repo_url,
)

TAG_ORDER = ("ai", "open-core", "non-osi", "new", "experimental")
DISPLAY_NAME = {"langchain": "LangChain", "neovim": "Neovim"}
TAG_MARK = {
    "ai": "🤖",
    "open-core": "💰",
    "non-osi": "⚠️",
    "new": "🌱",
    "experimental": "🧪",
}

APPENDIX_LISTS = [
    ("Awesome", "https://github.com/sindresorhus/awesome", "Curated list of awesome lists."),
    ("Awesome Hacking", "https://github.com/Hack-with-Github/Awesome-Hacking", "Curated list of hacking tools and resources."),
    ("Awesome Pentest", "https://github.com/enaqx/awesome-pentest", "Curated list of penetration testing resources."),
    ("Awesome Security", "https://github.com/sbilly/awesome-security", "Curated list of security software and resources."),
    ("Awesome Incident Response", "https://github.com/meirwah/awesome-incident-response", "Curated list of incident response tools."),
    ("Awesome DevSecOps", "https://github.com/devsecops/awesome-devsecops", "Curated list of DevSecOps tools."),
    ("Awesome Cloud Security", "https://github.com/4ndersonLin/awesome-cloud-security", "Curated list of cloud security resources."),
    ("Awesome LLM Security", "https://github.com/corca-ai/awesome-llm-security", "Curated list of large-language-model security resources."),
    ("Awesome AI Security", "https://github.com/ottosulin/awesome-ai-security", "Curated list of AI security resources."),
    ("Awesome AI Offensive Security", "https://github.com/yeyintminthuhtut/awesome-ai-offensive-security", "Curated list of AI tools for offensive security."),
    ("My Arsenal of AWS Security Tools", "https://github.com/toniblyx/my-arsenal-of-aws-security-tools", "Curated list of AWS security tools."),
    ("Awesome Endpoint Detection and Response", "https://github.com/shadawck/awesome-endpoint-detection-and-response", "Curated list of endpoint detection and response tools."),
    ("Awesome MCP Servers", "https://github.com/punkpeye/awesome-mcp-servers", "Curated list of Model Context Protocol servers."),
    ("Awesome Kubernetes Security", "https://github.com/magnologan/awesome-k8s-security", "Curated list of Kubernetes security tools."),
    ("Awesome LLM Cybersecurity Tools", "https://github.com/tenable/awesome-llm-cybersecurity-tools", "Archived curated list of LLM cybersecurity tools."),
]

APPENDIX_LABS = [
    ("OWASP Juice Shop", "https://github.com/juice-shop/juice-shop", "Intentionally insecure web application for security training."),
    ("OWASP WebGoat", "https://github.com/WebGoat/WebGoat", "Deliberately insecure web application for teaching web security."),
    ("OWASP Security Shepherd", "https://github.com/OWASP/SecurityShepherd", "Training platform for web and mobile application security."),
    ("VulnHub", "https://www.vulnhub.com", "Catalogue of vulnerable virtual machines for hands-on practice."),
]


def display_description(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned.endswith((".", "!", "?")):
        cleaned += "."
    first = cleaned.split()[0].strip(".,;:()[]")
    if first.isalpha() and first.islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    # awesome-lint asks for the product name "Git" and ignores the hyphenated form.
    cleaned = re.sub(r"(?<![\w.\-])git(?![\w.\-])", "Git", cleaned)
    return cleaned


def format_item(item: dict, metrics: dict | None) -> str:
    description = display_description(item["description"])
    tags = list(item.get("tags") or [])
    ordered = [tag for tag in TAG_ORDER if tag in tags]
    ordered.extend(tag for tag in tags if tag not in ordered)
    marks = [TAG_MARK.get(tag, tag) for tag in ordered]
    suffix = []
    if marks:
        suffix.append(" ".join(marks))
    if metrics:
        stats = []
        stars = format_count(metrics.get("stars"))
        if stars is not None:
            stats.append(f"⭐ {stars}")
        pushed = metrics.get("pushed_at") or ""
        if len(pushed) >= 7:
            stats.append(f"🕒 {pushed[:7]}")
        score = format_score(metrics.get("score"))
        if score is not None:
            stats.append(f"🎯 {score}")
        if stats:
            suffix.append(" · ".join(stats))
    subcategory = (item.get("subcategory") or "").strip()
    if subcategory:
        suffix.append(subcategory)
    tail = description if not suffix else description + " " + " · ".join(suffix)
    if not tail.endswith((".", "!", "?")):
        tail += "."
    name = DISPLAY_NAME.get(item["name"], item["name"])
    return f"- [{name}]({repo_url(item['repo'])}) - {tail}"


def _section(title: str, items: list[dict], metrics: dict[str, dict]) -> list[str]:
    lines = [f"### {title} ({len(items)})", ""]
    if not items:
        lines.append("None this round.")
        lines.append("")
        return lines
    for item in items:
        lines.append(format_item(item, metrics.get(item["repo"].lower())))
    lines.append("")
    return lines


def render(data_dir: Path = DATA, metrics_path: Path | None = None) -> str:
    metrics_path = metrics_path or latest_metrics_path(data_dir / "metrics")
    metrics = index_metrics(load_metrics(metrics_path))
    groups = []
    for group in GROUPS:
        document = load_yaml(data_dir / group["file"])
        items = document["items"]
        groups.append(
            {
                **group,
                "main": [item for item in items if item["tier"] == "main"],
                "watchlist": [item for item in items if item["tier"] == "watchlist"],
            }
        )
    toc = ["## Contents", ""]
    for group in groups:
        toc.append(f"- [{group['title']}](#{github_slug(group['title'])})")
    toc.append(f"- [Appendix](#{github_slug('Appendix')})")
    toc.append(f"- [Methodology](#{github_slug('Methodology')})")
    toc.append("")

    body = [
        "<!--lint disable awesome-github-->",
        "<!-- Generated by scripts/build.py. Edit data/*.yml, then regenerate. -->",
        "",
        "# Awesome Security Armory [![Awesome](https://awesome.re/badge.svg)](https://awesome.re)",
        "",
        "> Curated, scored list of open-source cybersecurity, AI security, AI agent skills, and AI-powered dev tools.",
        ">",
        "> Danh sách tuyển chọn, có chấm điểm, các công cụ mã nguồn mở về an ninh mạng, an ninh AI, kỹ năng cho AI agent và công cụ lập trình dùng AI.",
        "",
        "Main projects score at least 70 and are at least 90 days old. Watchlist holds newer projects, projects without an OSI license, and scores from 50 to 69. Each line is generated from `data/`. Do not edit this file by hand.",
        "",
        "Tags: 🤖 uses AI · 💰 open-core or a paid edition · ⚠️ license is not OSI · 🌱 younger than six months · 🧪 experimental. Figures: ⭐ stars · 🕒 month of the latest push · 🎯 score from 0 to 100.",
        "",
        *toc,
    ]
    for group in groups:
        body.append(f"## {group['title']}")
        body.append("")
        body.append(f"{len(group['main'])} Main, {len(group['watchlist'])} Watchlist.")
        body.append("")
        body.extend(_section("Main", group["main"], metrics))
        body.extend(_section("Watchlist", group["watchlist"], metrics))
    body.extend(
        [
            "## Appendix",
            "",
            "### Other awesome lists",
            "",
        ]
    )
    for name, url, description in APPENDIX_LISTS:
        body.append(f"- [{name}]({url}) - {description}")
    body.extend(["", "### Labs and practice environments", ""])
    for name, url, description in APPENDIX_LABS:
        body.append(f"- [{name}]({url}) - {description}")
    body.extend(
        [
            "",
            "Projects that were considered and not listed, with the reason, are recorded in [HISTORY.md](HISTORY.md).",
            "",
            "## Methodology",
            "",
            "Eight signals sum to 100: interest and growth 15, activity 15, contributors and bus factor 15, issue and pull-request responsiveness 15, security and OpenSSF Scorecard 15, dependents 10, license and docs 10, reputation and age 5. Counts use `log(1+x) / log(1+max(x, T))`, where T is the 90th percentile inside the same group, so a niche DFIR tool is not graded on the star scale of an AI coding agent.",
            "",
            "Missing inputs (90-day star growth until two snapshots exist, time to first response, notable users, and often Scorecard or dependents) are left blank. Their weight is redistributed. They are not scored as zero. Archived repos, missing repos, and repos with no push in 24 months are removed. A repo younger than 30 days is rejected. From 30 to 90 days, or without an OSI license, it can only sit on the Watchlist. About 15 Main projects are kept per group. A later move between Main and Watchlist waits for two consecutive weekly scores (72 up, under 65 down) unless a hard gate trips.",
            "",
            "The Main cut-off stays at 70 for v0.1. It will be recalibrated once star-growth, fresh Scorecard, and dependents data exist. Any change to that cut-off is proposed to Rex in its own pull request. The v0.1 collection notes, including known gaps, are in [SCORING_NOTES.md](SCORING_NOTES.md). Contribution rules are in [CONTRIBUTING.md](CONTRIBUTING.md).",
            "",
        ]
    )
    return "\n".join(body)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build README.md from data/")
    parser.add_argument("--check", action="store_true", help="Exit 1 if README.md is not the generated text")
    parser.add_argument("--output", type=Path, default=ROOT / "README.md")
    parser.add_argument("--data", type=Path, default=DATA)
    args = parser.parse_args(argv)
    text = render(args.data)
    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
        if current != text:
            print(f"{args.output} does not match scripts/build.py output", file=sys.stderr)
            return 1
        print("README.md matches")
        return 0
    args.output.write_text(text, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
