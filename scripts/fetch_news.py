# -*- coding: utf-8 -*-
"""新闻采集器：国际官方 (ITTF/WTT) + 国内主流体育媒体。

补齐「最新新闻」数据源。结构各异 → 归一化为 SCHEMA 中 news 字段。
本地无外网 → 默认 mock 演示数据，真实抓取在 GitHub Actions 执行。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

import config

log = logging.getLogger("fetch_news")


def _http_get(url: str, timeout: int = 30, retries: int = 2):
    import requests
    headers = {"User-Agent": config.USER_AGENT, "Accept": "application/json, text/plain, */*"}
    last_err = None
    for i in range(retries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            try:
                return r.json()
            except ValueError:
                return r.text
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            log.warning("新闻源请求失败 %s: %s", url, exc)
    if last_err:
        raise ConnectionError(f"新闻源请求失败 {url}: {last_err}") from last_err


def _pick(d: dict, *keys, default=None):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", []):
            return v
    return default


def _norm_item(it: dict, source: str) -> dict:
    title = _pick(it, "title", "Title", "name", "标题", default="")
    url = _pick(it, "url", "link", "Url", "原文链接", default="")
    published = _pick(it, "published_at", "publishedAt", "pubDate", "date", "时间", default="")
    summary = _pick(it, "summary_zh", "summary", "digest", "简介", "description", default="")
    # 中国相关判定
    blob = f"{title}{summary}"
    is_cn = any(kw.lower() in blob.lower() for kw in config.CHINESE_PLAYER_KEYWORDS)
    import hashlib
    nid = "news-" + hashlib.sha1((title + url).encode("utf-8")).hexdigest()[:12]
    return {
        "id": nid, "title": title, "source": source, "url": url,
        "published_at": published, "category": "media",
        "summary_zh": summary, "is_chinese_related": is_cn,
    }


def _adapt(data, source: str) -> list[dict]:
    items = (
        data.get("result", {}).get("data") or data.get("list") or data.get("data")
        or data.get("items") or data.get("items_list") or []
    ) if isinstance(data, dict) else (data or [])
    out = []
    for it in items:
        if isinstance(it, dict):
            out.append(_norm_item(it, source))
    return out


def fetch_news() -> list[dict]:
    if config.USE_MOCK:
        return _mock_news()
    out: list[dict] = []
    for src in config.SOURCE_CONFIG.get("news", {}).get("sources", []):
        try:
            data = _http_get(src["url"], config.SOURCE_CONFIG["news"].get("timeout", 30))
            out.extend(_adapt(data, src["name"]))
        except Exception as exc:  # noqa: BLE001
            log.warning("跳过新闻源 %s: %s", src["name"], exc)
    return out


def _mock_news() -> list[dict]:
    now = datetime.now()
    return [
        {
            "id": "news-mock-1",
            "title": "WTT 冠军赛：国乒主力悉数晋级 王楚钦顺利过关",
            "source": "WTT官网", "url": "https://worldtabletennis.com/",
            "published_at": (now - timedelta(hours=1)).isoformat(),
            "category": "result",
            "summary_zh": "WTT 冠军赛今日进行，国乒主力纷纷晋级。",
            "is_chinese_related": True,
        },
        {
            "id": "news-mock-2",
            "title": "孙颖莎赛后采访：状态稳步回升 期待更专注",
            "source": "新浪体育", "url": "https://sports.sina.com.cn/",
            "published_at": (now - timedelta(hours=3)).isoformat(),
            "category": "player_news",
            "summary_zh": "孙颖莎接受采访谈近期状态。",
            "is_chinese_related": True,
        },
        {
            "id": "news-mock-3",
            "title": "国际乒联更新世界排名 樊振东保持前三",
            "source": "ITTF", "url": "https://www.ittf.com/",
            "published_at": (now - timedelta(hours=5)).isoformat(),
            "category": "official",
            "summary_zh": "国际乒联公布最新一期世界排名。",
            "is_chinese_related": True,
        },
    ]


def fetch_domestic() -> list[dict]:
    """国内赛事（乒超/全运会/全国锦标赛）——先返回演示，真实来源需人工核实后接入。"""
    if config.USE_MOCK:
        return _mock_domestic()
    # TODO: 接入国内售票/协会/媒体源（人工核实）。当前返回空，由人工在 data/tournaments 增补。
    return []


def _mock_domestic() -> list[dict]:
    now = datetime.now().date()
    def d(offset): return (now + timedelta(days=offset)).isoformat()
    return [
        {
            "id": "china-super-league-2026", "name": "China Super League",
            "name_zh": "中国乒乓球超级联赛", "level": "china_super_league", "category": "domestic",
            "start_date": d(5), "end_date": d(40),
            "location": {"city": "北京", "country": "CHN", "venue": "首钢园"},
            "venue_zh": "首钢园", "format": {"type": "group+elimination"},
            "tickets": [{"tier": "常规赛", "price_zh": "¥100起", "currency": "CNY",
                         "buy_url": "https://www.damai.cn/"}],
            "status": "upcoming", "updated_at": now.isoformat(),
        },
    ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(fetch_news()[:3], ensure_ascii=False, indent=2))
