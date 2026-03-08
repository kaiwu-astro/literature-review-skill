#!/usr/bin/env python3
"""
provider_detector.py - 检测检索源是否可用（最小实现）

说明：
  - 本技能的检索实现主要为零配置 API（OpenAlex/Semantic Scholar/Crossref）。
  - NASA ADS 需要 API token（通过 ADS_API_TOKEN 环境变量或 config.yaml api.ads.token 配置）；
    未配置 token 时报告为不可用，避免 provider_priority 列表中 ads 在 openalex 之前时
    产生误导性的“OK”状态并短路后续检索。
  - MCP 属于宿主能力（工具/插件），不一定能在纯 Python 脚本内直接调用；
    因此这里对 MCP 的检测以“环境变量/显式配置”为准，并提供统一的可用性口径，
    以便 multi_query_search 进行自动降级。
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional


_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


@dataclass
class ProviderStatus:
    provider: str
    available: bool
    reason: str = ""


class ProviderDetector:
    def __init__(self, *, cache_ttl: int = 300, cache_enabled: bool = True):
        self.cache_ttl = int(cache_ttl)
        self.cache_enabled = bool(cache_enabled)
        self._cache: Dict[str, tuple[float, ProviderStatus]] = {}

    def detect(self, provider: str) -> ProviderStatus:
        provider = str(provider or "").strip()
        if not provider:
            return ProviderStatus(provider="", available=False, reason="empty provider")

        now = time.time()
        if self.cache_enabled and provider in self._cache:
            ts, st = self._cache[provider]
            if now - ts <= self.cache_ttl:
                return st

        st = self._detect_uncached(provider)
        if self.cache_enabled:
            self._cache[provider] = (now, st)
        return st

    def detect_many(self, providers: List[str]) -> Dict[str, ProviderStatus]:
        out: Dict[str, ProviderStatus] = {}
        for p in providers:
            st = self.detect(p)
            out[st.provider] = st
        return out

    def _detect_uncached(self, provider: str) -> ProviderStatus:
        if provider == "mcp":
            # MCP 一般由宿主工具提供；纯 Python 脚本内无法可靠探测。
            # 这里支持用户显式声明（例如在运行环境中注入该变量）。
            flag = os.environ.get("SLR_MCP_AVAILABLE", "").strip().lower()
            if flag in {"1", "true", "yes", "y"}:
                return ProviderStatus(provider="mcp", available=True, reason="SLR_MCP_AVAILABLE=true")
            return ProviderStatus(provider="mcp", available=False, reason="MCP 未在脚本环境中启用（可通过 SLR_MCP_AVAILABLE=true 显式声明）")

        if provider == "ads":
            # ADS 需要 token；先检查环境变量，再检查 config.yaml api.ads.token
            token = os.environ.get("ADS_API_TOKEN", "").strip()
            if not token:
                try:
                    import yaml  # type: ignore  # yaml 为可选依赖；不可用时跳过 config.yaml 检查
                    with _CONFIG_PATH.open(encoding="utf-8") as _f:
                        _cfg = yaml.safe_load(_f) or {}
                    ads_cfg = _cfg.get("api", {}).get("ads", {})
                    token = str(ads_cfg.get("token") or "").strip()
                except ImportError:
                    pass  # PyYAML 未安装，仅依赖环境变量
                except Exception:
                    pass  # config.yaml 不存在或解析失败，仅依赖环境变量
            if token:
                return ProviderStatus(provider="ads", available=True, reason="ADS token configured")
            return ProviderStatus(
                provider="ads",
                available=False,
                reason="ADS token 未配置（请设置环境变量 ADS_API_TOKEN 或在 config.yaml 的 api.ads.token 填入 token）",
            )

        # 零配置 API：默认认为可用（真正的网络可用性由调用阶段处理）
        if provider in {"openalex", "semantic_scholar", "crossref", "duckduckgo"}:
            return ProviderStatus(provider=provider, available=True, reason="assume available (runtime check)")

        return ProviderStatus(provider=provider, available=False, reason="unknown provider")


def main() -> int:
    parser = argparse.ArgumentParser(description="检测检索 provider 的可用性（轻量）")
    parser.add_argument("--providers", nargs="+", default=["mcp", "ads", "openalex", "semantic_scholar", "crossref"])
    parser.add_argument("--ttl", type=int, default=300)
    args = parser.parse_args()

    det = ProviderDetector(cache_ttl=args.ttl, cache_enabled=False)
    statuses = det.detect_many(args.providers)
    for p in args.providers:
        st = statuses.get(p)
        if st is None:
            continue
        print(f"{st.provider}: {'OK' if st.available else 'NO'} - {st.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
