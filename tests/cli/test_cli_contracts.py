from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_validate_counts_help() -> None:
    cp = subprocess.run(
        ["python3", "scripts/validate_counts.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0
    assert "--tex" in cp.stdout


def test_validate_counts_fail_on_missing_tex(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("review_levels:\n  default: premium\n", encoding="utf-8")

    cp = subprocess.run(
        [
            "python3",
            "scripts/validate_counts.py",
            "--tex",
            str(tmp_path / "missing.tex"),
            "--config",
            str(cfg),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert cp.returncode == 2
    assert "tex 不存在" in cp.stderr
