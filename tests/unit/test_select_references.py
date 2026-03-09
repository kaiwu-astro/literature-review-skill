from __future__ import annotations

import select_references


def test_select_papers_dedup_and_target() -> None:
    papers = [
        {"doi": "10.1/a", "title": "A", "year": 2020, "score": 9, "abstract": "x" * 100},
        {"doi": "10.1/a", "title": "A duplicate", "year": 2020, "score": 1, "abstract": "x" * 100},
        {"doi": "10.1/b", "title": "B", "year": 2021, "score": 8, "abstract": "x" * 100},
    ]
    selected, rationale = select_references._select_papers(
        papers,
        min_refs=1,
        max_refs=3,
        target_refs=2,
        high_score_min=0.5,
        high_score_max=0.5,
        min_abstract_chars=80,
    )

    assert len(selected) == 2
    assert rationale["total_candidates"] == 2


def test_select_papers_marks_missing_abstract_do_not_cite() -> None:
    papers = [
        {"doi": "10.1/a", "title": "A", "score": 9, "abstract": "x" * 100},
        {"doi": "10.1/b", "title": "B", "score": 8, "abstract": "short"},
    ]
    selected, rationale = select_references._select_papers(
        papers,
        min_refs=1,
        max_refs=3,
        target_refs=2,
        high_score_min=0.8,
        high_score_max=0.8,
        min_abstract_chars=80,
    )

    assert len(selected) == 2
    assert rationale["missing_abstract_selected"] == 1
    missing = [p for p in selected if p.get("doi") == "10.1/b"][0]
    assert missing["do_not_cite"] is True
    assert "missing_abstract" in missing["quality_warnings"]


def test_bib_key_uniqueness_case_insensitive() -> None:
    used: set[str] = set()
    k1 = select_references._make_unique_key("Ref", used)
    k2 = select_references._make_unique_key("ref", used)

    assert k1 == "Ref"
    assert k2 == "ref1"


def test_escape_bib_value_special_chars() -> None:
    escaped, counts = select_references._escape_bib_value("A&B_100%")

    assert escaped == r"A\&B\_100\%"
    assert counts["&"] == 1
    assert counts["_"] == 1
    assert counts["%"] == 1
