# -*- coding: utf-8 -*-
"""国际赛事采集器：ITTF / WTT。

设计要点：
- 端点可配置（见 config.SOURCE_CONFIG），按顺序尝试。
- 真实端点字段结构会变，因此解析层做「宽松匹配 + 容错」，缺字段就给默认值。
- 本地沙箱无外网（USE_MOCK=1 或网络失败）→ 回退到演示数据，保证整条链路可跑。
- 真实抓取在 GitHub Actions（有外网）执行。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

import config
from config import (
    USER_AGENT, CHINESE_PLAYER_KEYWORDS,
)

log = logging.getLogger("fetch_ittf")


# ---------------------------------------------------------------------------
# Http 工具：带重试
# ---------------------------------------------------------------------------
def _http_get(url: str, timeout: int = 30, retries: int = 2):
    import requests
    last_err: Exception | None = None
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    for i in range(retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            # 尝试解析 json；失败则返回文本
            try:
                return resp.json()
            except ValueError:
                return resp.text
        except Exception as exc:  # noqa: BLE001 —— 网络错误统一捕获
            last_err = exc
            log.warning("第 %d 次请求失败 %s: %s", i + 1, url, exc)
    if last_err:
        raise ConnectionError(f"所有重试失败 {url}: {last_err}") from last_err
    return None


# ---------------------------------------------------------------------------
# 宽松字段取值：从 dict 里按若干候选 key 取第一个非空值
# ---------------------------------------------------------------------------
def pick(obj: dict, *keys, default=None):
    for k in keys:
        v = obj.get(k)
        if v not in (None, "", []):
            return v
    return default


# ---------------------------------------------------------------------------
# 世界排名抓取 —— 返回 [{rank,player_id,name_zh,name,country,points,movement}]
# ---------------------------------------------------------------------------
def fetch_world_ranking() -> list[dict]:
    if config.USE_MOCK:
        return _mock_ranking()

    cfg = config.SOURCE_CONFIG["ittf"]
    url = cfg["base_url"].rstrip("/") + cfg["ranking_path"]
    data = _http_get(url, cfg["timeout"])
    # 结构未知：做宽松适配
    return _adapt_ranking(data)


def _adapt_ranking(data) -> list[dict]:
    """将可能的 ITTF/WTT 排名结构适配为统一格式。"""
    rows = []
    if isinstance(data, dict):
        # 尝试若干候选容器字段
        items = (
            data.get("list") or data.get("ranking") or data.get("data")
            or data.get("items") or []
        )
    elif isinstance(data, list):
        items = data
    else:
        items = []

    for idx, it in enumerate(items):
        if not isinstance(it, dict):
            continue
        name = pick(it, "name", "Name", "playerName", default="")
        name_zh = pick(it, "name_zh", "cnName", "name_cn", default=name)
        country = pick(it, "country", "Country", "nation", default="")
        points = pick(it, "points", "Points", "rating", default=0)
        rank = pick(it, "rank", "Rank", "place", "position", default=idx + 1)
        rows.append({
            "rank": int(rank) if str(rank).isdigit() else idx + 1,
            "player_id": pick(it, "playerId", "player_id", "id",
                              default=name_zh),
            "name_zh": name_zh,
            "name": name,
            "country": country,
            "points": int(points) if str(points).isdigit() else 0,
            "movement": pick(it, "movement", "move", "diff", default=0),
        })
    return rows


# ---------------------------------------------------------------------------
# 赛事日历抓取 —— 返回 tournament 归一化对象列表
# ---------------------------------------------------------------------------
def fetch_calendar() -> list[dict]:
    if config.USE_MOCK:
        return _mock_tournaments()

    cfg = config.SOURCE_CONFIG["ittf"]
    url = cfg["base_url"].rstrip("/") + cfg["calendar_path"]
    data = _http_get(url, cfg["timeout"])
    return _adapt_tournaments(data)


def _adapt_tournaments(data) -> list[dict]:
    items = (
        data.get("calendar") or data.get("events") or data.get("data")
        or data.get("list") or data.get("items") or []
    ) if isinstance(data, dict) else (data or [])
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        out.append(_normalize_tournament(it))
    return out


def _normalize_tournament(it: dict) -> dict:
    name = pick(it, "name", "Name", "title", default="")
    name_zh = pick(it, "name_zh", "cnName", default=name)
    level = pick(it, "level", "Level", "category", default="other")
    venue = pick(it, "venue", "Venue", default="")
    city = pick(it, "city", "City", default="")
    country = pick(it, "country", "Country", default="")
    start = pick(it, "startDate", "start_date", "from", default="")
    end = pick(it, "endDate", "end_date", "to", default="")
    return {
        "id": pick(it, "id", "eventId", default=f"evt-{hash(name) & 0xFFFFFF:x}"),
        "name": name,
        "name_zh": name_zh,
        "level": level,
        "category": "international",
        "start_date": _norm_date(start),
        "end_date": _norm_date(end) or _norm_date(start),
        "location": {"city": city, "country": country, "venue": venue},
        "venue_zh": venue,
        "format": {},
        "tickets": [],
        "status": _status_for(start, end),
        "updated_at": datetime.now().isoformat(),
    }


def _status_for(start: str, end: str) -> str:
    today = datetime.now().date()
    s = _parse_date(start) or today
    e = _parse_date(end) or today
    if s > today:
        return "upcoming"
    if e < today:
        return "completed"
    return "ongoing"


def _parse_date(d: str):
    if not d:
        return None
    s = str(d).strip()
    # 常见格式（标准库，避免依赖 python-dateutil，提升可移植性）
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d",
                "%d-%m-%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # ISO 8601（含时区）
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        return None


def _norm_date(d: str) -> str:
    pd = _parse_date(d)
    return pd.isoformat() if pd else ""


# ---------------------------------------------------------------------------
# 赛果抓取 —— 返回 match 归一化对象列表
# ---------------------------------------------------------------------------
def fetch_results() -> list[dict]:
    if config.USE_MOCK:
        return _mock_matches()

    cfg = config.SOURCE_CONFIG["ittf"]
    url = cfg["base_url"].rstrip("/") + cfg["results_path"]
    data = _http_get(url, cfg["timeout"])
    return _adapt_matches(data)


def _adapt_matches(data) -> list[dict]:
    items = (
        data.get("matches") or data.get("results") or data.get("data")
        or data.get("list") or data.get("items") or []
    ) if isinstance(data, dict) else (data or [])
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        out.append(_normalize_match(it))
    return out


def _normalize_match(it: dict) -> dict:
    def _player(pk):
        raw = it.get(pk)
        if not raw:
            return None
        if isinstance(raw, str):
            return {"id": raw, "name": raw, "name_zh": raw, "country": ""}
        p = raw
        if not p:
            return None
        rec = {
            "id": pick(p, "id", "playerId", default=""),
            "name": pick(p, "name", "Name", default=""),
            "name_zh": pick(p, "name_zh", "cnName", default=pick(p, "name", default="")),
            "country": pick(p, "country", "Country", default=""),
        }
        if not (rec.get("name_zh") or rec.get("name")):
            return None
        return rec

    a = _player("player_a") or _player("player1") or _player("A") or {}
    b = _player("player_b") or _player("player2") or _player("B") or {}
    sa = pick(it, "score_a", "scoreA", "scores_a", default=0)
    sb = pick(it, "score_b", "scoreB", "scores_b", default=0)
    name_a = (a.get("name_zh") or a.get("name") or "").lower()
    name_b = (b.get("name_zh") or b.get("name") or "").lower()
    has_cn = any(
        kw.lower() in name_a + name_b for kw in CHINESE_PLAYER_KEYWORDS
    )
    match_date = pick(it, "matchDate", "match_date", "date", "Date", default="")
    event = pick(it, "event", "Event", "category", default="men_singles")
    return {
        "id": pick(it, "id", "matchId", default=f"m-{hash(str(a)+str(b)) & 0xFFFFFF:x}"),
        "tournament_id": pick(it, "tournamentId", "tournament_id", default=""),
        "event": event,
        "round": pick(it, "round", "Round", default=""),
        "player_a": a,
        "player_b": b,
        "score_a": int(sa) if str(sa).isdigit() else 0,
        "score_b": int(sb) if str(sb).isdigit() else 0,
        "games": [],
        "winner": pick(it, "winner", "Winner", default=""),
        "match_date": _norm_date(match_date),
        "status": pick(it, "status", "Status", default="completed"),
        "has_chinese_player": has_cn,
    }


# ---------------------------------------------------------------------------
# Mock / 演示数据 —— 本地无外网验证整条链路用
# ---------------------------------------------------------------------------
def _mock_ranking() -> list[dict]:
    data = [
        {"rank": 1, "player_id": "wang-chuqin", "name_zh": "王楚钦", "name": "Wang Chuqin",
         "country": "CHN", "points": 7925, "movement": 0},
        {"rank": 2, "player_id": "fan-zhendong", "name_zh": "樊振东", "name": "Fan Zhendong",
         "country": "CHN", "points": 7243, "movement": 0},
        {"rank": 3, "player_id": "ma-long", "name_zh": "马龙", "name": "Ma Long",
         "country": "CHN", "points": 6850, "movement": 1},
        {"rank": 4, "player_id": "lin-gaoyuan", "name_zh": "林高远", "name": "Lin Gaoyuan",
         "country": "CHN", "points": 4810, "movement": -1},
        {"rank": 5, "player_id": "sun-yingsha", "name_zh": "孙颖莎", "name": "Sun Yingsha",
         "country": "CHN", "points": 9200, "movement": 0, "event": "women"},
        {"rank": 6, "player_id": "chen-meng", "name_zh": "陈梦", "name": "Chen Meng",
         "country": "CHN", "points": 7450, "movement": 0, "event": "women"},
    ]
    return data


def _mock_tournaments() -> list[dict]:
    base = datetime.now().date()
    def d(offset): return (base + timedelta(days=offset)).isoformat()
    return [
        {
            "id": "wtt-grand-smash-2026-02", "name": "WTT Grand Smash",
            "name_zh": "WTT 大满贯", "level": "grand_smash", "category": "international",
            "start_date": d(-30), "end_date": d(-15),
            "location": {"city": "Singapore", "country": "SGP", "venue": "Singapore Indoor Stadium"},
            "venue_zh": "新加坡室内体育馆", "format": {"type": "single_elimination"},
            "tickets": [{"tier": "首轮", "price_zh": "¥200起", "currency": "CNY"}],
            "status": "completed", "updated_at": datetime.now().isoformat(),
        },
        {
            "id": "wtt-champions-2026-02", "name": "WTT Champions",
            "name_zh": "WTT 冠军赛", "level": "champions", "category": "international",
            "start_date": d(-10), "end_date": d(2),
            "location": {"city": "杭州", "country": "CHN", "venue": "杭州奥体中心"},
            "venue_zh": "杭州奥体中心体育馆", "format": {"type": "single_elimination"},
            "tickets": [{"tier": "小组赛", "price_zh": "¥150起", "currency": "CNY"}],
            "status": "ongoing", "updated_at": datetime.now().isoformat(),
        },
        {
            "id": "china-super-league-2026", "name": "China Super League",
            "name_zh": "中国乒乓球超级联赛", "level": "china_super_league", "category": "domestic",
            "start_date": d(5), "end_date": d(40),
            "location": {"city": "北京", "country": "CHN", "venue": "首钢园"},
            "venue_zh": "首钢园", "format": {"type": "group+elimination"},
            "tickets": [{"tier": "常规赛", "price_zh": "¥100起", "currency": "CNY"}],
            "status": "upcoming", "updated_at": datetime.now().isoformat(),
        },
    ]


def _mock_matches() -> list[dict]:
    return [
        {
            "id": "m-001", "tournament_id": "wtt-grand-smash-2026-02",
            "event": "men_singles", "round": "final",
            "player_a": {"id": "wang-chuqin", "name": "Wang Chuqin", "name_zh": "王楚钦", "country": "CHN"},
            "player_b": {"id": "fan-zhendong", "name": "Fan Zhendong", "name_zh": "樊振东", "country": "CHN"},
            "score_a": 4, "score_b": 1, "games": [{"a": 11, "b": 8}, {"a": 11, "b": 9}, {"a": 9, "b": 11}, {"a": 11, "b": 7}, {"a": 11, "b": 6}],
            "winner": "a", "match_date": (datetime.now() - timedelta(days=16)).date().isoformat(),
            "status": "completed", "has_chinese_player": True,
        },
        {
            "id": "m-002", "tournament_id": "wtt-grand-smash-2026-02",
            "event": "women_singles", "round": "final",
            "player_a": {"id": "sun-yingsha", "name": "Sun Yingsha", "name_zh": "孙颖莎", "country": "CHN"},
            "player_b": {"id": "chen-meng", "name": "Chen Meng", "name_zh": "陈梦", "country": "CHN"},
            "score_a": 4, "score_b": 2, "games": [{"a": 11, "b": 9}, {"a": 8, "b": 11}, {"a": 11, "b": 7}, {"a": 11, "b": 5}, {"a": 12, "b": 10}],
            "winner": "a", "match_date": (datetime.now() - timedelta(days=15)).date().isoformat(),
            "status": "completed", "has_chinese_player": True,
        },
    ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== mock 数据验证 ===")
    print(json.dumps(fetch_world_ranking()[:3], ensure_ascii=False, indent=2))
