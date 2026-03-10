"""Tests for Markdown support in validate_subtopic_count.py"""
from __future__ import annotations

from pathlib import Path
import validate_subtopic_count as vst


def test_count_subsections_markdown(tmp_path: Path):
    md = "\n".join([
        "# Review Title",
        "## Abstract",
        "Some abstract.",
        "## Introduction",
        "Intro text.",
        "## Deep Learning",
        "Body 1.",
        "## Natural Language Processing",
        "Body 2.",
        "## Computer Vision",
        "Body 3.",
        "## Discussion",
        "Discussion.",
        "## Conclusion",
        "Conclusion.",
        "## References",
        "- Ref 1",
    ])
    md_path = tmp_path / "test_review.md"
    md_path.write_text(md, encoding="utf-8")

    result = vst.count_subsections(md_path)
    assert result["subtopic_sections"] == 3  # Deep Learning, NLP, CV (H1 "Review Title" excluded)
    assert "Deep Learning" in result["subtopic_list"]
    assert "Natural Language Processing" in result["subtopic_list"]
    assert "Review Title" not in result["subtopic_list"]


def test_count_subsections_tex(tmp_path: Path):
    tex = r"""
\section{Abstract}
Text
\section{Introduction}
Text
\section{Deep Learning}
Body
\section{Discussion}
Text
\section{Conclusion}
Text
"""
    tex_path = tmp_path / "test_review.tex"
    tex_path.write_text(tex, encoding="utf-8")

    result = vst.count_subsections(tex_path)
    assert result["subtopic_sections"] == 1  # Deep Learning
    assert "Deep Learning" in result["subtopic_list"]
