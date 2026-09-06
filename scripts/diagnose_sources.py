# -*- coding: utf-8 -*-
"""数据源诊断：真实访问 ITTF/WTT/新闻端点，打印状态码与响应片段。

用于校准真实接口的返回结构。只打印、永不报错（返回 0）。
"""
from __future__ import annotations

import traceback

import config


def _probe(url: str, timeout: int = 20) -> tuple[int, str]:
    import requests
    r = requests.get(url, headers={"User-Agent": config.USER_AGENT}, timeout=timeout)
    snippet = (r.text or "")[:400].replace("\n", " ")
    return r.status_code, snippet


def main() -> int:
    print("=" * 70)
    print("数据源诊断 (probe real endpoints)")
    print("=" * 70)
    ittf = config.SOURCE_CONFIG.get("ittf", {})
    wtt = config.SOURCE_CONFIG.get("wtt", {})
    targets = [
        ("ITTF 日历", ittf.get("base_url", "") + ittf.get("calendar_path", "")),
        ("ITTF 赛果", ittf.get("base_url", "") + ittf.get("results_path", "")),
        ("ITTF 排名", ittf.get("base_url", "") + ittf.get("ranking_path", "")),
        ("WTT 站点", wtt.get("base_url", "") + wtt.get("api_path", "")),
    ]
    for label, url in targets:
        print(f"\n--- {label}: {url}")
        try:
            code, snippet = _probe(url)
            print(f"  HTTP {code}")
            print(f"  片段: {snippet!r}")
        except Exception as exc:  # noqa: BLE001
            print(f"  访问失败: {exc}")

    print("\n--- 新闻源")
    for src in config.SOURCE_CONFIG.get("news", {}).get("sources", []):
        try:
            code, snippet = _probe(src["url"])
            print(f"  {src['name']} ({src['url']}) -> HTTP {code}: {snippet!r}")
        except Exception as exc:  # noqa: BLE001
            print(f"  {src['name']} 访问失败: {exc}")
    print("\n" + "=" * 70)
    return 0


if __name__ == "__main__":
    main()
