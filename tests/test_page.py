"""The page and the SSH welcome in deploy/: every file they point to exists, and the shell script parses."""

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "page"


def test_page_references_exist():
    html = (PAGE / "index.html").read_text(encoding="utf-8")
    refs = set(re.findall(r'(?:src|href)="(assets/[^"]+)"', html))
    assert refs, "no assets referenced"
    missing = [r for r in refs if not (PAGE / r).is_file()]
    assert not missing, missing


def test_sample_matches_the_page():
    sample = json.loads((PAGE / "assets" / "sample.json").read_text())
    assert sample["sample_rate"] == 250
    assert len(sample["data"]) == 8
    assert {len(ch) for ch in sample["data"]} == {250 * sample["duration_s"]}
    assert "SIMULATED" in sample["note"]


def test_welcome_script_parses():
    subprocess.run(["sh", "-n", str(ROOT / "deploy" / "update-motd.d" / "05-welcome")], check=True)
