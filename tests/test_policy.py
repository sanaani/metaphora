"""The repo's own guard rails: data formats stay ignored and the leak check stays wired in."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def ignored(name: str) -> bool:
    r = subprocess.run(["git", "check-ignore", "-q", "--no-index", name], cwd=ROOT, check=False)
    return r.returncode == 0


def test_data_and_credentials_are_ignored():
    for name in ["data/x.json", "outputs/a.txt", "w.parquet", "v.npz", ".env", "openalex-key.txt"]:
        assert ignored(name), name


def test_code_and_docs_are_not_ignored():
    for name in ["src/metaphora/x.py", "docs/a.md", "results/phase-1/README.md"]:
        assert not ignored(name), name


def test_hooks_run_the_leak_check():
    for hook in ["pre-commit", "pre-push"]:
        assert "check-leaks.sh" in (ROOT / ".githooks" / hook).read_text()


def test_no_denylist_in_repo():
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    assert not [t for t in tracked.stdout.split() if "denylist" in t.lower()]
