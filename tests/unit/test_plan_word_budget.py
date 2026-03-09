from __future__ import annotations

from pathlib import Path

import plan_word_budget


def test_load_outline_default_contains_non_cited_sections() -> None:
    sections = plan_word_budget.load_outline(None, ["topic-a"])
    titles = [s.title for s in sections]
    assert "引言" in titles
    assert "讨论" in titles
    assert "展望" in titles
    assert "结论" in titles


def test_allocate_within_section_returns_empty_pid_for_non_cited() -> None:
    section = plan_word_budget.Section("s1", "引言", False, 1.0, None)
    rows = plan_word_budget.allocate_within_section(section, [], 100, 0.6, 0.4, 0.1)

    assert rows == [("", "引言", 60.0, 40.0)]


def test_run_once_is_deterministic_given_seed() -> None:
    sections = [
        plan_word_budget.Section("s1", "主题", True, None, "A"),
        plan_word_budget.Section("s2", "结论", False, 1.0, None),
    ]
    papers = [plan_word_budget.Paper("p1", "A", 8.0), plan_word_budget.Paper("p2", "A", 6.0)]
    cfg = {"ratio": {"cited": 0.7, "non_cited": 0.3}, "summary_ratio": 0.55, "commentary_ratio": 0.45, "noise_strength": 0.2}

    r1 = plan_word_budget.run_once(sections, papers, 1000, cfg, 17)
    r2 = plan_word_budget.run_once(sections, papers, 1000, cfg, 17)

    assert r1 == r2


def test_infer_target_words_reads_midpoint(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "scoring:\n  default_word_range:\n    premium:\n      min: 1000\n      max: 2000\n",
        encoding="utf-8",
    )

    target = plan_word_budget.infer_target_words(cfg, "premium")
    assert target == 1500
