# -*- coding: utf-8 -*-
"""数据质量校验：CI 阶段大声失败。返回非 0 表示数据有问题。"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from config import (
    TOURNAMENTS_DIR, MATCHES_DIR, RANKINGS_DIR, NEWS_DIR, PLAYERS_DIR, DAILY_DIR,
)

log = logging.getLogger("validate")

REQUIRED_MATCH_KEYS = ("id", "tournament_id", "event", "round", "status",
                       "player_a", "player_b", "score_a", "score_b")
REQUIRED_TOURNAMENT_KEYS = ("id", "name", "start_date", "status")
REQUIRED_RANK_KEYS = ("player_id", "name_zh", "rank", "points")


def _load(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        log.error("无法解析 %s: %s", path, exc)
        return None


def _expect(cond, msg) -> None:
    if isinstance(cond, bool):
        if not cond:
            _issues.append(msg)
    elif not cond:
        _issues.append(msg)


_issues: list[str] = []


def check() -> int:
    _issues.clear()

    tournaments = _load(TOURNAMENTS_DIR / "index.json", []) or []
    matches = _load(MATCHES_DIR / "index.json", []) or []
    ranking = _load(RANKINGS_DIR / "history.json", []) or []
    news = _load(NEWS_DIR / "index.json", []) or []
    players = _load(PLAYERS_DIR / "index.json", []) or []

    _expect(bool(tournaments), "没有赛事数据 (tournaments/index.json)")
    _expect(bool(matches), "没有比赛数据 (matches/index.json)")
    _expect(bool(news), "没有新闻数据 (news/index.json)")
    _expect(bool(ranking), "没有排名历史 (rankings/history.json)")
    _expect(bool(players), "没有球员数据 (players/index.json)")
    _expect(any(p.get("is_chinese") for p in players),
            "没有中国球员记录")

    for m in matches[:50]:
        miss = [k for k in REQUIRED_MATCH_KEYS if m.get(k) in (None, "")]
        if miss:
            _issues.append(f"比赛 {m.get('id')} 缺字段: {miss}")

    for t in tournaments[:50]:
        if not t.get("name_zh") and not t.get("name"):
            _issues.append(f"赛事 {t.get('id')} 缺名称")

    # 每日汇总
    daily_files = sorted(DAILY_DIR.glob("*.json"))
    _expect(bool(daily_files), "没有每日汇总文件")

    if _issues:
        log.error("数据校验未通过 (%d 项)：", len(_issues))
        for i in _issues:
            log.error("  - %s", i)
        return 1
    log.info("数据校验通过：赛事 %d · 比赛 %d · 新闻 %d · 球员 %d · 排名历史 %d 期",
             len(tournaments), len(matches), len(news), len(players), len(ranking))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sys.exit(check())
