# -*- coding: utf-8 -*-
"""每日汇总生成：读取当日数据，产出 data/daily/<YYYY-MM-DD>.json。

这是「企业微信/公众号每日推送」的内容源。输出包含：
- headline 一句话头条
- top_results 当日重点赛果（含中国球员者优先）
- top_news 当日重点新闻
- chinese_players 当日中国球员表现
- rankings_move 当日排名变动
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from config import (
    MATCHES_DIR, RANKINGS_DIR, NEWS_DIR, DAILY_DIR,
    CHINESE_PLAYER_KEYWORDS,
)

log = logging.getLogger("build_daily")


def _load_index(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _is_chinese(texts) -> bool:
    blob = " ".join(str(x) for x in texts if x).lower()
    return any(kw.lower() in blob for kw in CHINESE_PLAYER_KEYWORDS)


def build(today: str | None = None, share_url: str = "") -> dict:
    today = today or datetime.now().date().isoformat()
    log.info("生成每日汇总：%s", today)

    matches = _load_index(MATCHES_DIR / "index.json") or []
    news = _load_index(NEWS_DIR / "index.json") or []
    ranking = _load_index(RANKINGS_DIR / f"world-{today}.json") or []

    # 当日或进行中的中国球员重点赛果
    cn_matches = [
        m for m in matches
        if m.get("has_chinese_player")
        and m.get("status") in ("completed", "live")
        and (m.get("match_date") or today) >= today
    ]
    # 若无当日，就取最近含中国球员的 completed
    if not cn_matches:
        cn_matches = [
            m for m in matches if m.get("has_chinese_player")
            and m.get("status") == "completed"
        ][:5]

    # 中国球员姓名列表
    cn_names = sorted({n for m in cn_matches for n in
                       (m["player_a"].get("name_zh") or m["player_a"].get("name"),
                        m["player_b"].get("name_zh") or m["player_b"].get("name"))
                       if n and _is_chinese([n])})

    # 当日新闻（中国相关优先）
    today_news = [n for n in news if (n.get("published_at") or "")[:10] == today]
    today_news.sort(key=lambda n: n.get("is_chinese_related"), reverse=True)
    top_news = [{"title": n["title"], "source": n.get("source"),
                 "url": n.get("url")} for n in today_news[:5]]

    # 头条
    headline = _build_headline(cn_matches, today_news)

    summary = {
        "date": today,
        "headline": headline,
        "top_results": [
            {"round": m.get("round"), "event": m.get("event"),
             "player_a": m["player_a"]["name_zh"] or m["player_a"]["name"],
             "player_b": m["player_b"]["name_zh"] or m["player_b"]["name"],
             "score": f"{m.get('score_a')}-{m.get('score_b')}",
             "winner": ("A" if m.get("winner") == "a" else "B"),
             "tournament_id": m.get("tournament_id")} for m in cn_matches[:5]
        ],
        "top_news": top_news,
        "chinese_players": {\
            "active_count": len({n for m in cn_matches for n in
                                 ((m['player_a'].get('name_zh') or m['player_a'].get('name')),
                                  (m['player_b'].get('name_zh') or m['player_b'].get('name')))
                                 if n}),
            "names": cn_names,
        },
        "rankings_move": [
            {"name": r.get("name_zh"), "rank": r.get("rank"),
             "movement": r.get("movement")} for r in ranking[:10]
        ] if ranking else [],
        "share_url": share_url,
        "generated_at": datetime.now().isoformat(),
    }

    out = DAILY_DIR / f"{today}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("写每日汇总 → %s", out)
    return summary


def _build_headline(cn_matches: list[dict], news: list[dict]) -> str:
    if cn_matches:
        m = cn_matches[0]
        a = m["player_a"]["name_zh"] or m["player_a"]["name"]
        b = m["player_b"]["name_zh"] or m["player_b"]["name"]
        winner = "A" if m.get("winner") == "a" else "B"
        wname = a if winner == "A" else b
        return f"{wname} 在{m.get('round') or '比赛'}中以 {m.get('score_a')}-{m.get('score_b')} 战胜对手"
    if news:
        n = news[0]
        return n.get("title", "")
    return "今日暂无重点乒乓赛事信息"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build(share_url="https://example.com/")
