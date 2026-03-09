"""Tests for validate_review_markdown.py"""
from __future__ import annotations

from pathlib import Path
import json
import pytest

import validate_review_markdown as vrm


# ---------------------------------------------------------------------------
# extract_headings
# ---------------------------------------------------------------------------

def test_extract_headings_basic():
    md = "# Title\n## Section A\n### Sub\n## Section B\n"
    headings = vrm.extract_headings(md)
    assert headings == [(1, "Title"), (2, "Section A"), (3, "Sub"), (2, "Section B")]


# ---------------------------------------------------------------------------
# extract_doi_citations
# ---------------------------------------------------------------------------

def test_extract_doi_citations_single():
    md = "Some text [Smith et al. (2023)](https://doi.org/10.1234/abcd) more text."
    cites = vrm.extract_doi_citations(md)
    assert len(cites) == 1
    assert cites[0]["display"] == "Smith et al. (2023)"
    assert cites[0]["doi_url"] == "https://doi.org/10.1234/abcd"


def test_extract_doi_citations_multiple():
    md = (
        "A [Smith (2020)](https://doi.org/10.1/a); "
        "[Jones & Lee (2021)](https://doi.org/10.2/b)."
    )
    cites = vrm.extract_doi_citations(md)
    assert len(cites) == 2


def test_extract_doi_citations_excludes_references_section():
    md = (
        "Body [Smith (2020)](https://doi.org/10.1/a).\n\n"
        "## References\n\n"
        "- [Jones (2021)](https://doi.org/10.2/b)\n"
    )
    cites = vrm.extract_doi_citations(md)
    assert len(cites) == 1
    assert cites[0]["display"] == "Smith (2020)"


def test_extract_unique_dois():
    md = (
        "[A (2020)](https://doi.org/10.1/a) and [B (2021)](https://doi.org/10.2/b) "
        "and again [A (2020)](https://doi.org/10.1/a)."
    )
    dois = vrm.extract_unique_dois(md)
    assert len(dois) == 2


# ---------------------------------------------------------------------------
# extract_body_text & count_words
# ---------------------------------------------------------------------------

def test_extract_body_text():
    md = (
        "## Introduction\n\n"
        "This is [a link](https://example.com) with **bold** text.\n\n"
        "## References\n\n- Ref 1\n"
    )
    body = vrm.extract_body_text(md)
    assert "Introduction" in body
    assert "a link" in body
    assert "bold" in body
    assert "Ref 1" not in body


def test_count_words_mixed():
    total, cn, en, digits = vrm.count_words("中文A test 2024")
    assert cn == 2
    assert en == 1
    assert digits == 1
    assert total == 3


# ---------------------------------------------------------------------------
# check_required_sections
# ---------------------------------------------------------------------------

def test_check_required_sections_all_present():
    md = "\n".join([
        "## Abstract",
        "Some abstract text",
        "## Introduction",
        "Intro text",
        "## Deep Learning",
        "Body text",
        "## Discussion",
        "Discussion text",
        "## Conclusion",
        "Conclusion text",
    ])
    errors, info = vrm.check_required_sections(md)
    assert len(errors) == 0
    assert info["abstract"] is True
    assert info["intro"] is True
    assert info["body_count"] >= 1
    assert info["discussion"] is True
    assert info["outlook"] is True


def test_check_required_sections_missing_abstract():
    md = "\n".join([
        "## Introduction",
        "Text",
        "## Method",
        "Text",
        "## Discussion",
        "Text",
        "## Conclusion",
        "Text",
    ])
    errors, info = vrm.check_required_sections(md)
    assert any("摘要" in e for e in errors)
    assert info["abstract"] is False


# ---------------------------------------------------------------------------
# validate_harvard_display
# ---------------------------------------------------------------------------

def test_validate_harvard_display_valid():
    assert vrm.validate_harvard_display("Smith et al. (2023)") is True
    assert vrm.validate_harvard_display("Smith & Jones (2021)") is True
    assert vrm.validate_harvard_display("Wang (n.d.)") is True


def test_validate_harvard_display_invalid():
    assert vrm.validate_harvard_display("(2023) Smith") is False
    assert vrm.validate_harvard_display("Smith 2023") is False


# ---------------------------------------------------------------------------
# validate (integration)
# ---------------------------------------------------------------------------

def test_validate_complete_markdown(tmp_path: Path):
    md_content = "\n".join([
        "## Abstract",
        "This is an abstract.",
        "## Introduction",
        "Introduction text [Smith et al. (2023)](https://doi.org/10.1234/test).",
        "## Deep Learning Methods",
        "Body text [Jones & Lee (2021)](https://doi.org/10.5678/test2).",
        "## Discussion",
        "Discussion text.",
        "## Conclusion",
        "Conclusion text.",
        "",
        "## References",
        "- Smith et al. (2023). [Title](https://doi.org/10.1234/test)",
    ])
    md_path = tmp_path / "test_review.md"
    md_path.write_text(md_content, encoding="utf-8")

    # Create a matching bib file
    bib_content = '@article{smith2023, doi = {10.1234/test}}\n@article{jones2021, doi = {10.5678/test2}}\n'
    bib_path = tmp_path / "refs.bib"
    bib_path.write_text(bib_content, encoding="utf-8")

    passed, errors, sections = vrm.validate(md_path, bib_path=bib_path)
    assert passed is True, f"Unexpected errors: {errors}"
    assert sections["body_count"] >= 1


def test_validate_missing_doi_fails(tmp_path: Path):
    md_content = "\n".join([
        "## Abstract", "Abstract.",
        "## Introduction",
        "Text [Smith (2023)](https://doi.org/10.1234/known).",
        "Also [Unknown (2023)](https://doi.org/10.9999/unknown).",
        "## Topic", "Body.",
        "## Discussion", "Disc.",
        "## Conclusion", "Conc.",
    ])
    md_path = tmp_path / "test_review.md"
    md_path.write_text(md_content, encoding="utf-8")

    bib_content = '@article{smith2023, doi = {10.1234/known}}\n'
    bib_path = tmp_path / "refs.bib"
    bib_path.write_text(bib_content, encoding="utf-8")

    passed, errors, _ = vrm.validate(md_path, bib_path=bib_path)
    assert passed is False
    assert any("不在参考文献中" in e for e in errors)
