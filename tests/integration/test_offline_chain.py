from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"


def run(cmd: list[str], workdir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=workdir, text=True, capture_output=True, check=False)


def test_dedupe_select_word_budget_chain(tmp_path: Path) -> None:
    deduped = tmp_path / "papers_deduped.jsonl"
    merge_map = tmp_path / "merge_map.json"
    selected = tmp_path / "selected.jsonl"
    bib = tmp_path / "references.bib"
    rationale = tmp_path / "selection_rationale.yaml"
    artifacts = tmp_path / "artifacts"

    cp1 = run(
        [
            "python3",
            "scripts/dedupe_papers.py",
            "--input",
            str(FIXTURES / "papers_raw.jsonl"),
            "--output",
            str(deduped),
            "--map",
            str(merge_map),
        ],
        ROOT,
    )
    assert cp1.returncode == 0, cp1.stderr

    cp2 = run(
        [
            "python3",
            "scripts/select_references.py",
            "--input",
            str(deduped),
            "--output",
            str(selected),
            "--bib",
            str(bib),
            "--selection",
            str(rationale),
            "--min-refs",
            "2",
            "--max-refs",
            "3",
            "--target-refs",
            "3",
            "--min-abstract-chars",
            "20",
        ],
        ROOT,
    )
    assert cp2.returncode == 0, cp2.stderr

    cp3 = run(
        [
            "python3",
            "scripts/plan_word_budget.py",
            "--selected",
            str(selected),
            "--config",
            str(FIXTURES / "test_config.yaml"),
            "--output-dir",
            str(artifacts),
            "--review-level",
            "premium",
        ],
        ROOT,
    )
    assert cp3.returncode == 0, cp3.stderr

    assert bib.exists()
    assert rationale.exists()
    assert (artifacts / "word_budget_final.csv").exists()

    stats = json.loads(cp2.stdout.strip())
    assert stats["selected"] == 3
