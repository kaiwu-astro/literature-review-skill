from __future__ import annotations

import validate_counts


def test_extract_body_removes_math_comments_and_commands() -> None:
    tex = r"""
\documentclass{article}
\begin{document}
正文中文 ABC % 注释
$E=mc^2$
\section{标题}更多内容
\begin{verbatim}ignore me\end{verbatim}
\end{document}
"""
    body, notes = validate_counts.extract_body(tex)

    assert "注释" not in body
    assert "E=mc" not in body
    assert "ignore me" not in body
    assert "标题" in body
    assert notes


def test_count_words_counts_cn_en_digits() -> None:
    total, cn, en, digits = validate_counts.count_words("中文A test 2024")
    assert cn == 2
    assert en == 1
    assert digits == 1
    assert total == 3


def test_extract_cite_keys_deduplicates() -> None:
    tex = r"Text \cite{a,b} and \citet[see]{b,c}."
    keys = validate_counts.extract_cite_keys(tex)
    assert keys == {"a", "b", "c"}


def test_load_thresholds_prefers_override() -> None:
    config = {
        "validation": {
            "words": {"min": {"premium": 100}, "max": {"premium": 300}},
            "references": {"min": {"premium": 10}, "max": {"premium": 20}},
        }
    }
    min_words, min_cites, max_words, max_cites = validate_counts.load_thresholds(config, "premium", 120, 12)
    assert (min_words, min_cites, max_words, max_cites) == (120, 12, 300, 20)
