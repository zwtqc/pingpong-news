# -*- coding: utf-8 -*-
"""解析/管道自测：用贴近真实数据结构验证适配器健壮性。

本地无外网无法实测 ITTF/WTT，本文件用「真实字段形状」的样本验证解析层。
运行：python scripts/test_pipeline.py   （无外部依赖）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fetch_ittf, fetch_news, standardize, build_daily

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}")


def test_ranking_adapter():
    print("[adapt_ranking]")
    # ITTF 官网常见字段形状
    raw = {
        "list": [
            {"rank": 1, "playerName": "Wang Chuqin", "cnName": "王楚钦",
             "country": "CHN", "rating": 7925, "move": 0},
            {"rank": 2, "playerName": "Fan Zhendong", "cnName": "樊振东",
             "country": "CHN", "rating": 7243, "move": -1},
        ]
    }
    out = fetch_ittf._adapt_ranking(raw)
    check("解析出2条", len(out) == 2)
    check("rank字段", out[0]["rank"] == 1)
    check("points来自rating", out[0]["points"] == 7925)
    check("中文名映射", out[0]["name_zh"] == "王楚钦")
    check("movement", out[1]["movement"] == -1)


def test_tournament_adapter():
    print("[adapt_tournaments]")
    raw = {
        "events": [
            {"id": "wtt-smash", "Name": "WTT Grand Smash", "cnName": "WTT 大满贯",
             "level": "grand_smash", "Venue": "Singapore Indoor Stadium",
             "City": "Singapore", "Country": "SGP",
             "startDate": "2026-02-01", "endDate": "2026-02-10"},
        ]
    }
    out = fetch_ittf._adapt_tournaments(raw)
    check("解析出1条", len(out) == 1)
    check("id", out[0]["id"] == "wtt-smash")
    check("中/英文名", out[0]["name_zh"] == "WTT 大满贯" and out[0]["name"])
    check("场馆", out[0]["location"]["venue"] == "Singapore Indoor Stadium")
    check("默认国际", out[0]["category"] == "international")


def test_match_adapter():
    print("[adapt_matches]")
    raw = {
        "matches": [
            {"id": "m1", "matchId": "m1", "tournamentId": "wtt-smash",
             "category": "men_singles", "Round": "final",
             "player1": {"id": "wang", "name": "Wang Chuqin", "cnName": "王楚钦", "country": "CHN"},
             "player2": {"id": "fan", "name": "Fan Zhendong", "cnName": "樊振东", "country": "CHN"},
             "scores_a": 4, "scores_b": 1, "Winner": "player1",
             "date": "2026-02-09", "status": "completed"},
        ]
    }
    out = fetch_ittf._adapt_matches(raw)
    check("解析出1条", len(out) == 1)
    m = out[0]
    check("比分", m["score_a"] == 4 and m["score_b"] == 1)
    check("选手映射", m["player_a"]["name_zh"] == "王楚钦"
          and m["player_b"]["name_zh"] == "樊振东")
    check("中国球员标记", m["has_chinese_player"] is True)
    check("winner", m["winner"] == "player1")


def test_news_adapter():
    print("[adapt_news]")
    raw = {
        "data": [
            {"title": "WTT 冠军赛：王楚钦顺利晋级", "publishedAt": "2026-02-09T10:00:00Z",
             "summary": "国乒主力晋级"},
        ]
    }
    out = fetch_news._adapt(raw, "WTT官网")
    check("解析出1条", len(out) == 1)
    check("中国相关", out[0]["is_chinese_related"] is True)
    check("来源", out[0]["source"] == "WTT官网")


def test_standardize_dedupe():
    print("[standardize]")
    items = [{"id": "a"}, {"id": "b"}, {"id": "a"}]
    dedup = standardize.dedupe(items, "id")
    check("去重", len(dedup) == 2)
    check("校验比赛", standardize.validate_match(
        {"player_a": {"name": "A"}, "player_b": {"name": "B"}, "score_a": 1}) is True)
    check("拒绝空对战", standardize.validate_match(
        {"player_a": {}, "player_b": {}, "score_a": 1}) is False)


def test_build_daily():
    print("[build_daily]")
    import config
    config.DAILY_DIR.mkdir(parents=True, exist_ok=True)
    matches = [{
        "id": "m1", "tournament_id": "t1", "event": "men_singles", "round": "final",
        "player_a": {"name_zh": "王楚钦", "name": "Wang", "country": "CHN"},
        "player_b": {"name_zh": "樊振东", "name": "Fan", "country": "CHN"},
        "score_a": 4, "score_b": 1, "winner": "a", "match_date": "2026-02-09",
        "status": "completed", "has_chinese_player": True,
    }]
    d = build_daily.build("2026-02-09", share_url="https://x/")
    check("头条包含比分", "4-1" in (d.get("headline") or ""))
    check("有重点赛果", len(d.get("top_results") or []) >= 1)
    check("share_url", d.get("share_url") == "https://x/")


def test_h2h():
    print("[generate_site.build_h2h]")
    from generate_site import build_h2h
    matches = [
        {"id": "1", "status": "completed", "winner": "a",
         "player_a": {"id": "wang", "name_zh": "王楚钦", "country": "CHN"},
         "player_b": {"id": "fan", "name_zh": "樊振东", "country": "CHN"}},
        {"id": "2", "status": "completed", "winner": "b",
         "player_a": {"id": "wang", "name_zh": "王楚钦", "country": "CHN"},
         "player_b": {"id": "fan", "name_zh": "樊振东", "country": "CHN"}},
    ]
    out = build_h2h(matches)
    check("一对交锋", len(out) == 1)
    check("胜负统计", out[0]["wins_a"] == 1 and out[0]["wins_b"] == 1)


def main():
    print("== 乒乓资讯 · 解析/管道自测 ==")
    for fn in (test_ranking_adapter, test_tournament_adapter, test_match_adapter,
               test_news_adapter, test_standardize_dedupe, test_build_daily,
               test_h2h):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            global FAIL
            FAIL += 1
            print(f"  ✗ {fn.__name__} 异常: {exc}")
    print(f"\n结果：通过 {PASS} · 失败 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
