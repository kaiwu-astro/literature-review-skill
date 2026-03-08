#!/usr/bin/env python3
"""
ads_search.py - NASA ADS 检索并生成 papers.jsonl

定位：
  - 为天文/天体物理主题提供核心检索源（NASA ADS）
  - 支持 API token 从环境变量 ADS_API_TOKEN 或 config.yaml 读取
  - token 缺失时优雅降级（返回空结果并打印提示）
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests  # type: ignore

from api_cache import CacheStorage
from config_loader import get_api_config, load_config
from exponential_backoff_retry import ExponentialBackoffRetry


_DOI_RE = re.compile(r"(10\.[0-9]{4,9}/[-._;()/:A-Za-z0-9]+)", re.IGNORECASE)


def _normalize_doi(raw: str) -> str:
    if not raw:
        return ""
    s = raw.strip()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^doi:\s*", "", s, flags=re.IGNORECASE).strip()
    m = _DOI_RE.search(s)
    return (m.group(1) if m else s).lower()


def _paper_to_minimal(doc: Dict[str, Any]) -> Dict[str, Any]:
    title_list = doc.get("title") or []
    title = str(title_list[0]).strip() if isinstance(title_list, list) and title_list else str(doc.get("title") or "").strip()

    doi_list = doc.get("doi") or []
    doi_raw = doi_list[0] if isinstance(doi_list, list) and doi_list else doc.get("doi") or ""
    doi = _normalize_doi(str(doi_raw or ""))

    authors = []
    for a in (doc.get("author") or [])[:10]:
        name = str(a or "").strip()
        if name:
            authors.append(name)

    bibstem = doc.get("bibstem") or []
    venue = str((bibstem[0] if isinstance(bibstem, list) and bibstem else doc.get("pub") or "")).strip()
    year = doc.get("year")

    url = ""
    bibcode = str(doc.get("bibcode") or "").strip()
    if bibcode:
        url = f"https://ui.adsabs.harvard.edu/abs/{bibcode}/abstract"

    abstract = str(doc.get("abstract") or "").strip()

    return {
        "title": title,
        "doi": doi,
        "abstract": abstract,
        "venue": venue,
        "year": year,
        "url": url,
        "authors": authors,
        "source": "ads",
    }


def search_ads(
    query: str,
    max_results: int = 50,
    *,
    token: Optional[str] = None,
    timeout: Optional[int] = None,
    cache_dir: Optional[Path] = None,
    retry: Optional[ExponentialBackoffRetry] = None,
) -> List[Dict[str, Any]]:
    if not query.strip():
        return []

    cfg = load_config()
    api_cfg = get_api_config("ads", cfg)
    base_url = str(api_cfg.get("base_url") or "https://api.adsabs.harvard.edu/v1").rstrip("/")
    timeout = int(timeout or api_cfg.get("timeout", 15))

    if token is None:
        token = os.environ.get("ADS_API_TOKEN") or str(api_cfg.get("token") or "").strip()

    if not token:
        print("[ads_search] ADS token 缺失，已优雅降级（返回空结果）。设置 ADS_API_TOKEN 或 config.yaml api.ads.token。")
        return []

    retry = retry or ExponentialBackoffRetry(((cfg.get("search") or {}).get("rate_limit_protection") or {}).get("retry") or {})
    cache = CacheStorage(cache_dir=cache_dir, ttl=86400) if cache_dir is not None else None

    endpoint = f"{base_url}/search/query"
    rows = min(200, max(1, int(max_results)))
    fl = "title,author,year,doi,abstract,bibcode,bibstem,pub"

    def do_request(start: int) -> Dict[str, Any]:
        params = {
            "q": query,
            "rows": rows,
            "start": start,
            "fl": fl,
            "sort": "date desc",
        }
        if cache is not None:
            cached = cache.get(endpoint, params)
            if cached is not None:
                return cached

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "systematic-literature-review ads-search",
        }
        resp = requests.get(endpoint, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        if cache is not None:
            cache.set(endpoint, params, data)
        return data

    out: List[Dict[str, Any]] = []
    start = 0
    while len(out) < max_results:
        data = retry.call(do_request, start)
        docs = ((data.get("response") or {}).get("docs") or []) if isinstance(data, dict) else []
        if not docs:
            break

        for d in docs:
            if isinstance(d, dict):
                out.append(_paper_to_minimal(d))
            if len(out) >= max_results:
                break

        if len(docs) < rows:
            break
        start += len(docs)

    seen = set()
    deduped: List[Dict[str, Any]] = []
    for p in out:
        key = p.get("doi") or f'{p.get("title", "").strip().lower()}::{p.get("year")}'
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(p)
        if len(deduped) >= max_results:
            break

    return deduped


def main() -> int:
    parser = argparse.ArgumentParser(description="Search NASA ADS and write papers.jsonl")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--output", required=True, type=Path, help="Output .jsonl path")
    parser.add_argument("--max-results", type=int, default=50, help="Max results (default: 50)")
    parser.add_argument("--token", default=None, help="ADS API token (optional; fallback to ADS_API_TOKEN)")
    parser.add_argument("--cache-dir", type=Path, default=None, help="API cache directory path (optional)")
    args = parser.parse_args()

    papers = search_ads(
        query=args.query,
        max_results=args.max_results,
        token=args.token,
        cache_dir=args.cache_dir,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for paper in papers:
            f.write(json.dumps(paper, ensure_ascii=False) + "\n")

    print(json.dumps({"query": args.query, "written": len(papers), "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
