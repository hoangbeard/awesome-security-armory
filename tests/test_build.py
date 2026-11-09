from common import ROOT
from build import display_description, format_item, render


def test_bullet_uses_text_stats_not_badges():
    line = format_item(
        {
            "repo": "usestrix/strix",
            "name": "Strix",
            "description": "Autonomous AI agents that pentest applications and suggest fixes.",
            "tags": ["ai", "open-core"],
            "subcategory": "AI Pentest Agents",
            "tier": "main",
        },
        {"stars": 74500, "pushed_at": "2026-11-09T00:00:00Z", "score": 86},
    )
    assert line == (
        "- [Strix](https://github.com/usestrix/strix) - "
        "Autonomous AI agents that pentest applications and suggest fixes. "
        "🤖 💰 · ⭐ 74.5k · 🕒 2026-11 · 🎯 86 · AI Pentest Agents."
    )
    assert "![" not in line
    assert "http" not in line.split("](")[1].split(")")[0] or line.startswith("- [Strix](https://github.com/")


def test_lowercase_first_word_is_capitalized_for_the_readme_only():
    assert display_description("cat clone with syntax highlighting.") == "Cat clone with syntax highlighting."
    assert display_description("eBPF-based runtime security.") == "eBPF-based runtime security."
    assert display_description("Detects secrets in git repos.") == "Detects secrets in Git repos."
    assert ".gitignore" in display_description("Recursive search that respects .gitignore.")
    assert "git-aware" in display_description("AI pair programming with git-aware edits.")


def test_rendered_readme_lists_groups_in_order():
    text = render(ROOT / "data")
    assert text.startswith("<!--lint disable awesome-github-->")
    assert "# Awesome Security Armory [" in text
    assert "Curated, scored list of open-source cybersecurity, AI security, AI agent skills, and AI-powered dev tools." in text
    positions = [text.index(f"## {title}") for title in (
        "AI Coding Agents & Harness",
        "AI Skills",
        "LLM, Agent Framework & MCP",
        "AI Security",
        "Offensive / Red Team",
        "Defensive / Blue Team",
        "Cloud & Kubernetes Security",
        "DevSecOps / AppSec",
        "Software & Dev Tools",
        "Appendix",
        "Methodology",
    )]
    assert positions == sorted(positions)
    assert "### Main (15)" in text
    assert "### Watchlist (1)" in text
    assert "[HISTORY.md](HISTORY.md)" in text
    assert "<img" not in text
    assert "shields.io" not in text
