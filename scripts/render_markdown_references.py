#!/usr/bin/env python3
"""
render_markdown_references.py - 为 Markdown 综述生成 Harvard 引用映射与 References 段落

输入：selected_papers.jsonl
输出：
  - 引用映射 JSON（cite_key → Harvard 显示文本 + DOI 链接）
  - ## References 段落（可直接附加到 Markdown 正文末尾）

统一处理：作者截断（et al.）、年份缺失、DOI 规范化、https://doi.org/ 前缀补全
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote as _url_quote


def _normalize_doi(doi: Optional[str]) -> Optional[str]:
    """规范化 DOI：确保以 https://doi.org/ 开头，并对路径部分做 URL 编码。

    对 DOI 路径做 URL 编码（保留 `/` 和 `#` 分隔符），以处理含 `)` 等保留字符的
    legacy SICI 风格 DOI，避免生成的 Markdown 链接截断。
    """
    if not doi:
        return None
    doi = doi.strip()
    if not doi:
        return None
    # 移除已有前缀
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:", "DOI:"):
        if doi.lower().startswith(prefix.lower()):
            doi = doi[len(prefix):]
            break
    doi = doi.strip().strip("/")
    if not doi:
        return None
    # URL 编码：保留 / 和 # 作为路径/片段分隔符，其余保留字符需编码
    encoded = _url_quote(doi, safe="/:@!$&'*+,;=#~.-_")
    return f"https://doi.org/{encoded}"


def _format_authors_harvard(authors: Any) -> str:
    """将作者列表格式化为 Harvard 风格：Smith et al. 或 Smith & Jones"""
    if not authors:
        return "Unknown"
    if isinstance(authors, str):
        # 优先按分号分隔，其次按 " and " 分隔
        if ";" in authors:
            parts = [a.strip() for a in authors.split(";") if a.strip()]
        elif " and " in authors.lower():
            parts = [a.strip() for a in re.split(r"\s+and\s+", authors, flags=re.IGNORECASE) if a.strip()]
        else:
            # 单个作者名（可能含逗号如 "Last, First"）
            parts = [authors.strip()]
        if not parts:
            return authors.strip() or "Unknown"
        authors = parts

    if isinstance(authors, list):
        if len(authors) == 0:
            return "Unknown"
        # 取第一作者的姓
        first = _extract_surname(authors[0])
        if len(authors) == 1:
            return first
        elif len(authors) == 2:
            second = _extract_surname(authors[1])
            return f"{first} & {second}"
        else:
            return f"{first} et al."
    return str(authors).strip() or "Unknown"


def _extract_surname(name: Any) -> str:
    """从作者名中提取姓"""
    if not name:
        return "Unknown"
    name = str(name).strip()
    if not name:
        return "Unknown"
    # 格式1：Last, First
    if "," in name:
        return name.split(",")[0].strip()
    # 格式2：First Last
    parts = name.split()
    if parts:
        return parts[-1].strip()
    return name


def _format_year(year: Any) -> str:
    """格式化年份"""
    if not year:
        return "n.d."
    y = str(year).strip()
    if not y:
        return "n.d."
    # 取前4位数字
    m = re.search(r"\d{4}", y)
    return m.group(0) if m else y


def build_citation_map(papers: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    从文献列表构建引用映射

    返回：{cite_key: {display: "Smith et al. (2023)", doi_url: "https://doi.org/...", ...}}
    """
    citation_map: Dict[str, Dict[str, Any]] = {}
    for paper in papers:
        doi_raw = paper.get("doi") or ""
        doi_url = _normalize_doi(doi_raw)

        # 跳过无 DOI 的文献（Markdown 正文不可引用）
        if not doi_url:
            continue

        authors = paper.get("authors") or paper.get("author") or []
        year = paper.get("year") or paper.get("publication_year") or ""
        title = paper.get("title") or ""

        author_display = _format_authors_harvard(authors)
        year_display = _format_year(year)

        display_text = f"{author_display} ({year_display})"

        # cite_key 优先使用 bib_key / id
        cite_key = paper.get("bib_key") or paper.get("cite_key") or paper.get("id") or ""
        if not cite_key:
            # 以 DOI 为兜底 key
            cite_key = doi_raw.strip()
        if not cite_key:
            continue

        citation_map[cite_key] = {
            "display": display_text,
            "doi_url": doi_url,
            "markdown_cite": f"[{display_text}]({doi_url})",
            "title": title.strip(),
            "year": year_display,
            "authors_harvard": author_display,
        }
    return citation_map


def render_references_section(citation_map: Dict[str, Dict[str, Any]]) -> str:
    """生成 ## References 段落"""
    lines = ["## References", ""]
    # 按作者+年份排序
    sorted_entries = sorted(
        citation_map.values(),
        key=lambda e: (e.get("authors_harvard", "").lower(), e.get("year", "")),
    )
    for entry in sorted_entries:
        title = entry.get("title", "")
        doi_url = entry.get("doi_url", "")
        display = entry.get("display", "")
        if doi_url and title:
            lines.append(f"- {display}. [{title}]({doi_url})")
        elif title:
            lines.append(f"- {display}. {title}")
        else:
            lines.append(f"- {display}.")
    lines.append("")
    return "\n".join(lines)


def load_papers_from_jsonl(path: Path) -> List[Dict[str, Any]]:
    """加载 JSONL 文件中的文献列表"""
    papers: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                papers.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return papers


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Harvard citation mapping and References section for Markdown reviews"
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to selected_papers.jsonl",
    )
    parser.add_argument(
        "--output-map",
        type=Path,
        default=None,
        help="Path to output citation map JSON (optional)",
    )
    parser.add_argument(
        "--output-references",
        type=Path,
        default=None,
        help="Path to output References section Markdown (optional)",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"✗ 输入文件不存在: {args.input}", file=sys.stderr)
        return 1

    papers = load_papers_from_jsonl(args.input)
    if not papers:
        print(f"✗ 未找到有效文献: {args.input}", file=sys.stderr)
        return 1

    citation_map = build_citation_map(papers)
    print(f"✓ 构建引用映射: {len(citation_map)} 篇（有 DOI）", file=sys.stderr)

    if args.output_map:
        args.output_map.parent.mkdir(parents=True, exist_ok=True)
        args.output_map.write_text(
            json.dumps(citation_map, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"✓ 引用映射已保存: {args.output_map}", file=sys.stderr)

    references_section = render_references_section(citation_map)

    if args.output_references:
        args.output_references.parent.mkdir(parents=True, exist_ok=True)
        args.output_references.write_text(references_section, encoding="utf-8")
        print(f"✓ References 段落已保存: {args.output_references}", file=sys.stderr)

    # 将 References 输出到 stdout 供管道使用
    print(references_section)
    return 0


if __name__ == "__main__":
    sys.exit(main())
