# -*- coding: utf-8 -*-
"""数据标准化与落盘：去重、校验、过滤中国球员、写入 data/ 目录。"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

from config import (
    TOURNAMENTS_DIR, MATCHES_DIR, RANKINGS_DIR, NEWS_DIR, PLAYERS_DIR,
    CHINESE_PLAYER_KEYWORDS,
)

log = logging.getLogger("standardize")


def _stable_id(*parts) -> str:
    raw = "|".join(str(p) for p in parts if p)
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return h


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 校验工具
# ---------------------------------------------------------------------------
def validate_tournament(t: dict) -> bool:
    return bool(t.get("name") or t.get("name_zh")) and bool(t.get("id"))


def validate_match(m: dict) -> bool:
    a, b = m.get("player_a"), m.get("player_b")
    return bool(a and b) and bool(m.get("score_a") is not None)


def is_chinese_related(*texts) -> bool:
    blob = " ".join(str(x) for x in texts if x).lower()
    return any(kw.lower() in blob for kw in CHINESE_PLAYER_KEYWORDS)


# ---------------------------------------------------------------------------
# 去重
# ---------------------------------------------------------------------------
def dedupe(items: list[dict], key="id") -> list[dict]:
    seen = set()
    out = []
    for it in items:
        k = it.get(key)
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out


# ---------------------------------------------------------------------------
# 标准化主流程
# ---------------------------------------------------------------------------
def standardize_tournaments(raw: list[dict]) -> list[dict]:
    """写赛事文件到 data/tournaments/<id>.json，并维护索引 index.json。"""
    valid = [t for t in dedupe(raw, "id") if validate_tournament(t)]
    for t in valid:
        write_json(TOURNAMENTS_DIR / f"{t['id']}.json", t)
    # 索引
    index = [{k: t.get(k) for k in ("id", "name", "name_zh", "level",
                                    "category", "start_date", "end_date",
                                    "status", "venue_zh")} for t in valid]
    write_json(TOURNAMENTS_DIR / "index.json", index)
    log.info("标准化赛事 %d 条", len(valid))
    return valid


def standardize_matches(raw: list[dict]) -> list[dict]:
    """写比赛文件到 data/matches/<id>.json，维护按日期泛化的索引。"""
    valid = [m for m in dedupe(raw, "id") if validate_match(m)]
    for m in valid:
        write_json(MATCHES_DIR / f"{m['id']}.json", m)
    # 按日期分组聚合，供站点读取
    by_date: dict[str, list[str]] = {}
    for m in valid:
        d = m.get("match_date") or "unknown"
        by_date.setdefault(d, []).append(m["id"])
    write_json(MATCHES_DIR / "by_date.json", by_date)
    write_json(MATCHES_DIR / "index.json", [
        {k: m.get(k) for k in ("id", "tournament_id", "event", "round", "match_date",
                               "status", "has_chinese_player", "score_a", "score_b",
                               "player_a", "player_b", "winner")} for m in valid
    ])
    log.info("标准化比赛 %d 条", len(valid))
    return valid


def standardize_ranking(raw: list[dict], rank_date: str) -> list[dict]:
    """写单期排名，并聚合到 history.json。"""
    valid = dedupe(raw, "player_id")
    write_json(RANKINGS_DIR / f"world-{rank_date}.json", valid)

    # 聚合历史（追加并去重）
    hist_path = RANKINGS_DIR / "history.json"
    hist = []
    if hist_path.exists():
        hist = json.loads(hist_path.read_text(encoding="utf-8"))
    hist.append({"date": rank_date, "ranking": valid})
    dedup_hist = {h["date"]: h for h in hist}
    write_json(hist_path, sorted(dedup_hist.values(), key=lambda h: h["date"]))
    log.info("标准化排名 %d 条 @ %s", len(valid), rank_date)
    return valid


def standardize_news(raw: list[dict]) -> list[dict]:
    """写新闻文件到 data/news/<id>.json。"""
    valid = [n for n in dedupe(raw, "id") if n.get("title")]
    for n in valid:
        write_json(NEWS_DIR / f"{n['id']}.json", n)
    write_json(NEWS_DIR / "index.json", [
        {k: n.get(k) for k in ("id", "title", "source", "published_at",
                               "category", "is_chinese_related")} for n in valid
    ])
    log.info("标准化新闻 %d 条", len(valid))
    return valid


def build_players(ranking: list[dict], matches: list[dict]) -> list[dict]:
    """从排名 + 赛果派生中国球员资料库，写 data/players/<id>.json + index.json。

    字段：id, name, name_zh, country, is_chinese, world_rank, world_points,
          titles(近3个月冠军), recent_matches
    """
    from collections import defaultdict

    players: dict[str, dict] = {}

    def ensure(pid, name="", name_zh="", country=""):
        rec = players.setdefault(pid, {
            "id": pid, "name": name, "name_zh": name_zh, "country": country,
            "is_chinese": False, "world_rank": None, "world_points": None,
            "titles": [], "recent_matches": [],
        })
        if name and not rec["name"]:
            rec["name"] = name
        if name_zh and not rec["name_zh"]:
            rec["name_zh"] = name_zh
        if country and not rec["country"]:
            rec["country"] = country
        return rec

    # 1) 从排名进入
    for r in ranking:
        pid = r.get("player_id") or _player_id(r.get("name_zh") or r.get("name"))
        rec = ensure(pid, r.get("name", ""), r.get("name_zh", ""), r.get("country", ""))
        rec["world_rank"] = r.get("rank")
        rec["world_points"] = r.get("points")
        rec["is_chinese"] = rec["is_chinese"] or _is_chinese_player(r)

    # 2) 从赛果进入
    for m in matches:
        for side in ("player_a", "player_b"):
            p = m.get(side) or {}
            name_zh = p.get("name_zh") or p.get("name") or ""
            name = p.get("name") or ""
            pid = p.get("id") or _player_id(name_zh)
            rec = ensure(pid, name, name_zh, p.get("country", ""))
        # 近3个月冠军：completed 决赛胜者
        if m.get("round") == "final" and m.get("status") == "completed" and m.get("winner"):
            winner = m["player_a"] if m["winner"] == "a" else m["player_b"]
            tid = m.get("tournament_id", "")
            rec = ensure(winner.get("id") or _player_id(winner.get("name_zh")),
                         winner.get("name"), winner.get("name_zh"), winner.get("country"))
            yaer = (m.get("match_date") or "")[:4]
            rec["titles"].append({"tournament_id": tid, "year": yaer})
        # 近期赛果
        if m.get("status") == "completed":
            for side, other in (("player_a", "player_b"), ("player_b", "player_a")):
                p = m.get(side) or {}
                o = m.get(other) or {}
                pid = p.get("id") or _player_id(p.get("name_zh") or p.get("name"))
                rec = ensure(pid, p.get("name"), p.get("name_zh"), p.get("country"))
                won_char = "a" if side == "player_a" else "b"
                rec["recent_matches"].append({
                    "date": m.get("match_date"), "opponent": o.get("name_zh") or o.get("name"),
                    "score": f"{m.get('score_a')}-{m.get('score_b')}",
                    "won": (m.get("winner") == won_char),
                })

    # 3) 标记中国球员 & 去重 titles/recent
    out = []
    for rec in players.values():
        rec["is_chinese"] = rec["is_chinese"] or rec["country"] == "CHN"
        rec["titles"] = _dedup(rec["titles"], "tournament_id")
        rec["recent_matches"].sort(key=lambda x: x.get("date") or "", reverse=True)
        write_json(PLAYERS_DIR / f"{rec['id']}.json", rec)
        out.append(rec)

    # 仅展示中国球员为主，但保留全部（含外国选手）利于总览
    out.sort(key=lambda p: (not p["is_chinese"], p.get("world_rank") or 999))
    write_json(PLAYERS_DIR / "index.json", [
        {k: p.get(k) for k in ("id", "name", "name_zh", "country", "is_chinese",
                               "world_rank", "world_points")} for p in out
    ])
    cn = [p for p in out if p["is_chinese"]]
    write_json(PLAYERS_DIR / "china.json", [
        {k: p.get(k) for k in ("id", "name", "name_zh", "country", "is_chinese",
                               "world_rank", "world_points")} for p in cn
    ])
    log.info("派生球员 %d 名（中国球员 %d）", len(out), len(cn))
    return out


def _is_chinese_player(rec) -> bool:
    blob = " ".join(str(x) for x in (rec.get("name_zh"), rec.get("name"), rec.get("country"))).lower()
    return rec.get("country") == "CHN" or any(kw.lower() in blob for kw in CHINESE_PLAYER_KEYWORDS)


def _player_id(name: str) -> str:
    return "p-" + _stable_id(name)


def _dedup(items: list[dict], key: str) -> list[dict]:
    seen, out = set(), []
    for it in items:
        k = it.get(key)
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from fetch_ittf import fetch_world_ranking, fetch_calendar, fetch_results
    tournaments = standardize_tournaments(fetch_calendar())
    matches = standardize_matches(fetch_results())
    ranking = standardize_ranking(fetch_world_ranking(), datetime.now().date().isoformat())
    build_players(ranking, matches)
    print("标准化完成")
