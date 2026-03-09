"""Tests for render_markdown_references.py"""
from __future__ import annotations

import json
from pathlib import Path

import render_markdown_references as rmr


# ---------------------------------------------------------------------------
# _normalize_doi
# ---------------------------------------------------------------------------

def test_normalize_doi_full_url():
    assert rmr._normalize_doi("https://doi.org/10.1234/test") == "https://doi.org/10.1234/test"


def test_normalize_doi_bare():
    assert rmr._normalize_doi("10.1234/test") == "https://doi.org/10.1234/test"


def test_normalize_doi_with_prefix():
    assert rmr._normalize_doi("doi:10.1234/test") == "https://doi.org/10.1234/test"


def test_normalize_doi_empty():
    assert rmr._normalize_doi("") is None
    assert rmr._normalize_doi(None) is None


# ---------------------------------------------------------------------------
# _format_authors_harvard
# ---------------------------------------------------------------------------

def test_format_authors_harvard_single():
    assert rmr._format_authors_harvard(["John Smith"]) == "Smith"


def test_format_authors_harvard_two():
    result = rmr._format_authors_harvard(["John Smith", "Jane Doe"])
    assert result == "Smith & Doe"


def test_format_authors_harvard_three_plus():
    result = rmr._format_authors_harvard(["Smith, J.", "Doe, J.", "Lee, K."])
    assert result == "Smith et al."


def test_format_authors_harvard_empty():
    assert rmr._format_authors_harvard([]) == "Unknown"
    assert rmr._format_authors_harvard(None) == "Unknown"


def test_format_authors_harvard_string():
    result = rmr._format_authors_harvard("Smith, J.; Doe, J.; Lee, K.")
    assert "Smith" in result
    assert "et al." in result


def test_format_authors_harvard_string_single_with_comma():
    # "Last, First" pattern should be treated as a single author
    result = rmr._format_authors_harvard("Smith, John")
    assert result == "Smith"


# ---------------------------------------------------------------------------
# _format_year
# ---------------------------------------------------------------------------

def test_format_year_int():
    assert rmr._format_year(2023) == "2023"


def test_format_year_none():
    assert rmr._format_year(None) == "n.d."


def test_format_year_empty():
    assert rmr._format_year("") == "n.d."


# ---------------------------------------------------------------------------
# build_citation_map
# ---------------------------------------------------------------------------

def test_build_citation_map_basic():
    papers = [
        {
            "bib_key": "smith2023",
            "doi": "10.1234/test",
            "authors": ["John Smith", "Jane Doe"],
            "year": 2023,
            "title": "A Great Paper",
        },
    ]
    cmap = rmr.build_citation_map(papers)
    assert "smith2023" in cmap
    entry = cmap["smith2023"]
    assert entry["display"] == "Smith & Doe (2023)"
    assert entry["doi_url"] == "https://doi.org/10.1234/test"
    assert "[Smith & Doe (2023)]" in entry["markdown_cite"]


def test_build_citation_map_no_doi_skipped():
    papers = [
        {"bib_key": "no_doi", "authors": ["Test"], "year": 2020, "title": "No DOI"},
    ]
    cmap = rmr.build_citation_map(papers)
    assert len(cmap) == 0


# ---------------------------------------------------------------------------
# render_references_section
# ---------------------------------------------------------------------------

def test_render_references_section():
    cmap = {
        "smith2023": {
            "display": "Smith (2023)",
            "doi_url": "https://doi.org/10.1234/test",
            "title": "A Paper",
            "year": "2023",
            "authors_harvard": "Smith",
        },
    }
    refs = rmr.render_references_section(cmap)
    assert "## References" in refs
    assert "[A Paper](https://doi.org/10.1234/test)" in refs
    assert "Smith (2023)" in refs


# ---------------------------------------------------------------------------
# load_papers_from_jsonl
# ---------------------------------------------------------------------------

def test_load_papers_from_jsonl(tmp_path: Path):
    data = [
        {"id": "1", "doi": "10.1/a", "title": "Paper A"},
        {"id": "2", "doi": "10.2/b", "title": "Paper B"},
    ]
    jsonl_path = tmp_path / "papers.jsonl"
    jsonl_path.write_text(
        "\n".join(json.dumps(d) for d in data) + "\n",
        encoding="utf-8",
    )
    papers = rmr.load_papers_from_jsonl(jsonl_path)
    assert len(papers) == 2
