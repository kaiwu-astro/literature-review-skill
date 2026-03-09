#!/usr/bin/env python3
"""
validate_review_markdown.py - Markdown 综述校验：必需章节 + DOI 引用对齐 + 引用数量

校验内容：
  - 必需章节是否存在（摘要/引言/子主题段落/讨论/展望/结论）
  - 正文词数统计
  - 提取 Markdown DOI 引用（Harvard referencing 链接）并统计唯一引用数
  - 校验正文引用与 selected_papers / .bib 中的 DOI 对齐
  - 校验引用显示文本是否符合 Harvard referencing 规则
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Markdown 标题提取
# ---------------------------------------------------------------------------

def extract_headings(md: str) -> List[Tuple[int, str]]:
    """提取 Markdown 标题，返回 [(level, title), ...]"""
    headings: List[Tuple[int, str]] = []
    for line in md.splitlines():
        m = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            headings.append((level, title))
    return headings


# ---------------------------------------------------------------------------
# DOI 引用提取（Harvard referencing Markdown 链接）
# ---------------------------------------------------------------------------

_DOI_LINK_RE = re.compile(
    r"\[([^\]]+)\]"                    # 显示文本
    r"\("                               # (
    r"(https?://doi\.org/[^\s)]+)"      # DOI URL
    r"\)",                              # )
)


def extract_doi_citations(md: str) -> List[Dict[str, str]]:
    """
    提取正文中的 Markdown DOI 引用链接

    返回：[{display: "Smith et al. (2023)", doi_url: "https://doi.org/..."}]
    """
    citations: List[Dict[str, str]] = []
    # 排除 ## References 段落
    body = _strip_references_section(md)
    for m in _DOI_LINK_RE.finditer(body):
        citations.append({
            "display": m.group(1).strip(),
            "doi_url": m.group(2).strip(),
        })
    return citations


def extract_unique_dois(md: str) -> Set[str]:
    """提取正文中所有唯一 DOI URL"""
    citations = extract_doi_citations(md)
    return {c["doi_url"].rstrip("/").lower() for c in citations}


def _strip_references_section(md: str) -> str:
    """移除 ## References 及后续内容，只保留正文部分"""
    pattern = re.compile(r"^##\s+References\b", re.IGNORECASE | re.MULTILINE)
    m = pattern.search(md)
    if m:
        return md[:m.start()]
    return md


# ---------------------------------------------------------------------------
# 正文词数统计（格式无关，复用 validate_counts 的逻辑）
# ---------------------------------------------------------------------------

def extract_body_text(md: str) -> str:
    """从 Markdown 提取纯正文文本（去标题标记、链接语法等）"""
    body = _strip_references_section(md)
    # 去 Markdown 链接，保留显示文本
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)
    # 去标题标记
    body = re.sub(r"^#{1,6}\s+", "", body, flags=re.MULTILINE)
    # 去加粗/斜体
    body = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", body)
    # 去行内代码
    body = re.sub(r"`[^`]+`", " ", body)
    # 去 HTML 标签
    body = re.sub(r"<[^>]+>", " ", body)
    # 合并空白
    body = re.sub(r"\s+", " ", body)
    return body.strip()


def count_words(text: str) -> Tuple[int, int, int, int]:
    """返回 (总计, 中文, 英文, 数字token)，与 validate_counts 口径一致"""
    cn_matches = re.findall(r"[\u4e00-\u9fff]", text)
    en_matches = re.findall(r"\b[A-Za-z][A-Za-z0-9'-]*\b", text)
    digit_matches = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    cn_count = len(cn_matches)
    en_count = len(en_matches)
    digit_count = len(digit_matches)
    total = cn_count + en_count
    return total, cn_count, en_count, digit_count


# ---------------------------------------------------------------------------
# 章节校验
# ---------------------------------------------------------------------------

def _has_keyword(text: str, keywords: List[str]) -> bool:
    lowered = text.lower()
    return any(k.lower() in lowered for k in keywords)


def check_required_sections(md: str) -> Tuple[List[str], Dict[str, Any]]:
    """
    检查 Markdown 综述的必需章节

    返回：(errors, sections_info)
    """
    errors: List[str] = []
    headings = extract_headings(md)
    heading_titles = [t for _, t in headings]
    heading_titles_joined = "\n".join(heading_titles)

    musts = {
        "abstract": ["摘要", "Abstract", "Summary"],
        "intro": ["引言", "Introduction"],
        "discussion": ["讨论", "Discussion"],
        "outlook": ["展望", "Outlook", "Perspectives", "Conclusion", "结论"],
    }

    has_abstract = _has_keyword(heading_titles_joined, musts["abstract"])
    has_intro = _has_keyword(heading_titles_joined, musts["intro"])
    has_discussion = _has_keyword(heading_titles_joined, musts["discussion"])
    has_outlook = _has_keyword(heading_titles_joined, musts["outlook"])

    if not has_abstract:
        errors.append("缺少摘要（摘要/Abstract/Summary 标题）")
    if not has_intro:
        errors.append("缺少引言（引言/Introduction）")

    # 子主题段落：除标准章节外的标题
    standard_keywords = (
        list(musts["abstract"]) + list(musts["intro"]) + list(musts["discussion"])
        + list(musts["outlook"]) + ["References", "参考文献"]
    )
    body_titles = [
        t for t in heading_titles
        if not any(k.lower() in t.lower() for k in standard_keywords)
    ]
    if len(body_titles) < 1:
        errors.append("缺少至少 1 个子主题段落")

    if not has_discussion:
        errors.append("缺少讨论（讨论/Discussion）")
    if not has_outlook:
        errors.append("缺少展望/结论（展望/Outlook/Perspectives/结论）")

    sections_info = {
        "abstract": has_abstract,
        "intro": has_intro,
        "body_count": len(body_titles),
        "body_titles": body_titles[:10],
        "discussion": has_discussion,
        "outlook": has_outlook,
    }
    return errors, sections_info


# ---------------------------------------------------------------------------
# Harvard referencing 格式校验
# ---------------------------------------------------------------------------

_HARVARD_PATTERN = re.compile(
    r"^([A-Z\u4e00-\u9fff][\w\s&.'-]*?)\s*\((\d{4}|n\.d\.)\)$"
)


def validate_harvard_display(display: str) -> bool:
    """校验显示文本是否符合 Harvard referencing（Author (Year)）"""
    return bool(_HARVARD_PATTERN.match(display.strip()))


# ---------------------------------------------------------------------------
# 引用对齐校验
# ---------------------------------------------------------------------------

def _normalize_doi_for_compare(doi: str) -> str:
    """规范化 DOI 用于比较"""
    doi = doi.strip().lower().rstrip("/")
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:", "doi: "):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
            break
    return doi.strip()


def load_reference_dois(bib_path: Optional[Path], jsonl_path: Optional[Path]) -> Set[str]:
    """从 .bib 和/或 .jsonl 加载已知 DOI 集合"""
    dois: Set[str] = set()
    if bib_path and bib_path.exists():
        bib = bib_path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"doi\s*=\s*\{([^}]+)\}", bib, re.IGNORECASE):
            d = _normalize_doi_for_compare(m.group(1))
            if d:
                dois.add(d)
    if jsonl_path and jsonl_path.exists():
        with jsonl_path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                d = _normalize_doi_for_compare(str(obj.get("doi") or ""))
                if d:
                    dois.add(d)
    return dois


# ---------------------------------------------------------------------------
# 主校验入口
# ---------------------------------------------------------------------------

def validate(
    md_path: Path,
    bib_path: Optional[Path] = None,
    jsonl_path: Optional[Path] = None,
    min_refs: int = 0,
    max_refs: int = 0,
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    执行完整 Markdown 综述校验

    返回：(passed, errors, sections_info)
    """
    md = _read(md_path)
    errors: List[str] = []

    # 1. 必需章节
    section_errors, sections_info = check_required_sections(md)
    errors.extend(section_errors)

    # 2. DOI 引用
    body_citations = extract_doi_citations(md)
    unique_dois_in_body = set()
    for c in body_citations:
        d = _normalize_doi_for_compare(c["doi_url"])
        if d:
            unique_dois_in_body.add(d)

    if not unique_dois_in_body:
        errors.append("正文未包含任何 DOI 引用链接")
    else:
        if min_refs and len(unique_dois_in_body) < min_refs:
            errors.append(f"唯一引用数不足: {len(unique_dois_in_body)} < {min_refs}")
        if max_refs and len(unique_dois_in_body) > max_refs:
            errors.append(f"唯一引用数超出: {len(unique_dois_in_body)} > {max_refs}")

    # 3. 引用与参考文献对齐
    if bib_path or jsonl_path:
        ref_dois = load_reference_dois(bib_path, jsonl_path)
        if ref_dois:
            missing = sorted(unique_dois_in_body - ref_dois)
            if missing:
                shown = missing[:10]
                suffix = f" ... 共 {len(missing)} 个" if len(missing) > 10 else ""
                errors.append(
                    "正文引用 DOI 不在参考文献中: " + ", ".join(shown) + suffix
                )

    # 4. Harvard referencing 格式校验
    bad_displays: List[str] = []
    for c in body_citations:
        if not validate_harvard_display(c["display"]):
            bad_displays.append(c["display"])
    if bad_displays:
        shown = bad_displays[:5]
        suffix = f" ... 共 {len(bad_displays)} 处" if len(bad_displays) > 5 else ""
        errors.append(
            "引用显示文本不符合 Harvard referencing（Author (Year)）: "
            + "; ".join(f'"{d}"' for d in shown)
            + suffix
        )

    passed = len(errors) == 0
    return passed, errors, sections_info


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Markdown review: required sections + DOI citations + Harvard referencing"
    )
    parser.add_argument("--md", required=True, type=Path, help="Path to review.md")
    parser.add_argument("--bib", type=Path, default=None, help="Path to references.bib (optional)")
    parser.add_argument("--selected-jsonl", type=Path, default=None, help="Path to selected_papers.jsonl (optional)")
    parser.add_argument("--min-refs", type=int, default=0, help="Minimum unique DOI citations")
    parser.add_argument("--max-refs", type=int, default=0, help="Maximum unique DOI citations (0 = no limit)")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")
    args = parser.parse_args()

    if not args.md.exists():
        print(f"✗ 文件不存在: {args.md}", file=sys.stderr)
        return 1

    passed, errors, sections_info = validate(
        args.md,
        bib_path=args.bib,
        jsonl_path=args.selected_jsonl,
        min_refs=args.min_refs,
        max_refs=args.max_refs,
    )

    md = _read(args.md)
    body_text = extract_body_text(md)
    words_total, words_cn, words_en, words_digits = count_words(body_text)
    unique_dois = extract_unique_dois(md)

    if args.verbose:
        print(f"\n📊 Markdown 综述校验报告", file=sys.stderr)
        print(f"   文件: {args.md.name}", file=sys.stderr)
        print(f"   正文字数: {words_total}（中文 {words_cn}，英文 {words_en}）", file=sys.stderr)
        print(f"   唯一 DOI 引用: {len(unique_dois)}", file=sys.stderr)
        print(f"   章节信息: {json.dumps(sections_info, ensure_ascii=False)}", file=sys.stderr)

    if errors:
        print("Markdown review validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    sections_json = json.dumps(sections_info, ensure_ascii=False)
    print(f"✓ Markdown review validation passed (dois={len(unique_dois)}) SECTIONS:{sections_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
