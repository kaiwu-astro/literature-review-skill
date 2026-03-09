"""Tests for Markdown support in validate_counts.py"""
from __future__ import annotations

import validate_counts


def test_extract_body_markdown_strips_references():
    md = "# Title\n\nSome body text here.\n\n## References\n\n- Ref entry\n"
    body, notes = validate_counts.extract_body_markdown(md)
    assert "body text" in body
    assert "Ref entry" not in body
    assert any("References" in n for n in notes)


def test_extract_body_markdown_strips_links():
    md = "Text [Smith (2023)](https://doi.org/10.1/a) more.\n"
    body, _ = validate_counts.extract_body_markdown(md)
    assert "Smith (2023)" in body
    assert "doi.org" not in body


def test_extract_body_markdown_strips_headings():
    md = "## Introduction\n\nSome intro text.\n"
    body, _ = validate_counts.extract_body_markdown(md)
    assert "##" not in body
    assert "intro text" in body


def test_extract_doi_citations_markdown_basic():
    md = "Text [A (2020)](https://doi.org/10.1/a) and [B (2021)](https://doi.org/10.2/b)."
    dois = validate_counts.extract_doi_citations_markdown(md)
    assert len(dois) == 2


def test_extract_doi_citations_markdown_deduplicates():
    md = (
        "[A (2020)](https://doi.org/10.1/a) "
        "[A again (2020)](https://doi.org/10.1/a)"
    )
    dois = validate_counts.extract_doi_citations_markdown(md)
    assert len(dois) == 1


def test_extract_doi_citations_markdown_excludes_references():
    md = (
        "[A (2020)](https://doi.org/10.1/a)\n\n"
        "## References\n\n"
        "- [B (2021)](https://doi.org/10.2/b)\n"
    )
    dois = validate_counts.extract_doi_citations_markdown(md)
    assert len(dois) == 1
