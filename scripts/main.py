# -*- coding: utf-8 -*-
"""主调度：一键跑完整数据管道。

用法：
    python scripts/main.py            # 采集 + 标准化 + 每日汇总
    python scripts/main.py --mock     # 强制用演示数据（本地无外网）
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime

import config
from fetch_ittf import fetch_world_ranking, fetch_calendar, fetch_results
from fetch_news import fetch_news as fetch_news_data, fetch_domestic
from standardize import (
    standardize_tournaments, standardize_matches, standardize_ranking,
    standardize_news, build_players,
)
from build_daily import build
from standardize import standardize_ranking as _std_rank

log = logging.getLogger("main")


def _seed_mock_history() -> None:
    """mock 模式：生成近 8 周的历史排名快照，供「排名趋势」图表使用。"""
    import random
    from datetime import timedelta
    rng = random.Random(42)
    base_names = [
        {"player_id": "wang-chuqin", "name_zh": "王楚钦", "name": "Wang Chuqin", "country": "CHN", "pts": 7925},
        {"player_id": "fan-zhendong", "name_zh": "樊振东", "name": "Fan Zhendong", "country": "CHN", "pts": 7243},
        {"player_id": "ma-long", "name_zh": "马龙", "name": "Ma Long", "country": "CHN", "pts": 6850},
        {"player_id": "lin-gaoyuan", "name_zh": "林高远", "name": "Lin Gaoyuan", "country": "CHN", "pts": 4810},
        {"player_id": "sun-yingsha", "name_zh": "孙颖莎", "name": "Sun Yingsha", "country": "CHN", "pts": 9200},
        {"player_id": "chen-meng", "name_zh": "陈梦", "name": "Chen Meng", "country": "CHN", "pts": 7450},
    ]
    today = datetime.now().date()
    for week in range(8, 0, -1):
        d = (today - timedelta(weeks=week)).isoformat()
        rows = []
        for i, p in enumerate(base_names):
            drift = sum(rng.randint(-120, 90) for _ in range(3))
            rows.append({
                "rank": i + 1, "player_id": p["player_id"], "name_zh": p["name_zh"],
                "name": p["name"], "country": p["country"],
                "points": max(0, p["pts"] + drift), "movement": 0,
            })
        # 排名按积分重排
        rows.sort(key=lambda r: r["points"], reverse=True)
        for idx, r in enumerate(rows):
            r["rank"] = idx + 1
        _std_rank(rows, d)


def run(mock: bool) -> dict:
    config.ensure_dirs()
    if mock:
        config.USE_MOCK = True
        log.info("使用演示数据（mock）模式")
        _seed_mock_history()

    log.info("== 采集国际赛事 ==")
    tournaments = _safe(fetch_calendar, "国际赛事日历")
    matches = _safe(fetch_results, "国际赛果")
    ranking = _safe(fetch_world_ranking, "世界排名")

    log.info("== 采集新闻与国内赛事 ==")
    news = _safe(fetch_news_data, "新闻")
    domestic = _safe(fetch_domestic, "国内赛事")
    tournaments = tournaments + domestic

    log.info("== 标准化落盘 ==")
    standardize_tournaments(tournaments)
    standardize_matches(matches)
    standardize_ranking(ranking, datetime.now().date().isoformat())
    standardize_news(news)
    build_players(ranking, matches)

    log.info("== 每日汇总 ==")
    summary = build(share_url=os.environ.get("PP_SHARE_URL", ""))
    return summary


def _safe(fn, label):
    """执行采集函数；出错时降级为空结果，不让整条任务崩溃。"""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        log.warning("采集[%s]失败，降级为空数据：%s", label, exc)
        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--mock", action="store_true",
                   help="强制使用演示数据（本地无外网验证链路用）")
    args = p.parse_args()
    summary = run(args.mock or config.USE_MOCK)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
