from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _job_block(text: str) -> str:
    return text.split("\njobs:", 1)[1]


def test_workflows_are_least_privilege_and_pinned():
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    daily = (ROOT / ".github/workflows/daily-collect.yml").read_text(encoding="utf-8")
    weekly = (ROOT / ".github/workflows/weekly-rescore.yml").read_text(encoding="utf-8")
    assert "contents: read" in ci
    assert "contents: write" not in ci
    for text in (ci, daily, weekly):
        head = text.split("\njobs:", 1)[0]
        assert "contents: read" in head
        assert "contents: write" not in head
        assert "actions: write" not in text
    assert "contents: write" in _job_block(daily)
    assert "contents: write" in _job_block(weekly)
    assert 'cron: "0 23 * * *"' in daily
    assert 'cron: "0 13 * * 0"' in weekly
    for text in (ci, daily, weekly):
        for line in text.splitlines():
            if "uses:" in line and "actions/" in line or "lychee" in line:
                if line.strip().startswith("uses:"):
                    assert "@" in line
                    assert line.split("@", 1)[1].split()[0].strip()[:7] != "v"
    for text in (daily, weekly):
        assert "push origin main" not in text
        assert "git push --force" not in text
        assert "HEAD:${branch}" in (ROOT / "scripts/push_weekly.sh").read_text(encoding="utf-8")
    script = (ROOT / "scripts/push_weekly.sh").read_text(encoding="utf-8")
    assert "refusing to push" in script
    assert "--force" not in script


def test_push_script_rejects_main():
    import subprocess

    result = subprocess.run(
        ["bash", str(ROOT / "scripts/push_weekly.sh"), "--dry-run", "main", "nope", "README.md"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    allowed = subprocess.run(
        ["bash", str(ROOT / "scripts/push_weekly.sh"), "--dry-run", "weekly/2026-W46", "Weekly rescore", "README.md"],
        capture_output=True,
        text=True,
    )
    assert allowed.returncode == 0
    assert "weekly/2026-W46" in allowed.stdout
