# -*- coding: utf-8 -*-
"""静态站点生成器：读取 data/ 的 JSON，产出 public/ 下的静态 HTML 页面。

零外部依赖，用 Python 标准库完成。GitHub Actions 或本地均可直接 `python scripts/generate_site.py`。
产出目录：pingpong-news/public/（直接作为 GitHub Pages 站点根目录）。
"""
from __future__ import annotations

import html
import json
import logging
from datetime import datetime
from pathlib import Path

from config import (
    ROOT, DATA_DIR, TOURNAMENTS_DIR, MATCHES_DIR, RANKINGS_DIR,
    NEWS_DIR, DAILY_DIR, PLAYERS_DIR, BASE, SITE_URL,
)

log = logging.getLogger("generate_site")

PUBLIC_DIR = ROOT / "public"
CSS_PATH = Path(__file__).resolve().parent / "site_assets" / "styles.css"

ESCAPE = html.escape


def url(path: str) -> str:
    """拼接站点 base 前缀，保证 GitHub Pages 任意托管路径下链接可用。"""
    return BASE + path


# ---------------------------------------------------------------------------
# 数据加载（缺文件返回空）
# ---------------------------------------------------------------------------
def _read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def _latest_file(directory: Path, prefix: str, suffix: str = "json"):
    if not directory.exists():
        return None
    cands = sorted(directory.glob(f"{prefix}*.{suffix}"))
    return cands[-1] if cands else None


def load_all():
    today = datetime.now().date().isoformat()
    tournaments = _read_json(TOURNAMENTS_DIR / "index.json", []) or []
    matches = _read_json(MATCHES_DIR / "index.json", []) or []
    news = _read_json(NEWS_DIR / "index.json", []) or []
    daily = _read_json(DAILY_DIR / f"{today}.json", None)
    if not daily:
        d = _latest_file(DAILY_DIR, "")
        daily = _read_json(d, None) if d else None
    rank_file = _latest_file(RANKINGS_DIR, "world-")
    ranking = _read_json(rank_file, []) or [] if rank_file else []
    players = _read_json(PLAYERS_DIR / "index.json", []) or []
    china = _read_json(PLAYERS_DIR / "china.json", []) or []
    history = _read_json(RANKINGS_DIR / "history.json", []) or []

    # 每日汇总归档（按日期倒序）
    daily_list = []
    for f in sorted(DAILY_DIR.glob("*.json")):
        d = _read_json(f, {}) or {}
        daily_list.append({
            "date": d.get("date", f.stem),
            "headline": d.get("headline", ""),
            "url": f"daily-{f.stem}.html",
        })
    daily_list.sort(key=lambda x: x["date"], reverse=True)

    return {
        "tournaments": tournaments,
        "matches": matches,
        "news": news,
        "daily": daily or {},
        "daily_list": daily_list,
        "ranking": ranking,
        "players": players,
        "china": china,
        "history": history,
        "rank_date": rank_file.stem.replace("world-", "") if rank_file else "",
    }


# ---------------------------------------------------------------------------
# 布局
# ---------------------------------------------------------------------------
NAV = [
    ("index.html", "首页"),
    ("daily.html", "今日简报"),
    ("rankings.html", "排名"),
    ("players.html", "球员"),
    ("calendar.html", "赛事日历"),
    ("tournaments.html", "赛事"),
    ("h2h.html", "交锋"),
    ("charts.html", "图表"),
    ("news.html", "新闻"),
    ("watch-guide.html", "观赛"),
]


def base_layout(title: str, content: str, active: str) -> str:
    nav_items = "".join(
        f'<a href="{href}" class="{"active" if href == active else ""}">{label}</a>'
        for href, label in NAV
    )
    # 分享/SEO meta（微信、社媒分享卡片用）
    abs_path = SITE_URL + BASE + "/" + active if SITE_URL else (BASE + "/" + active)
    og_title = title
    og_desc = "乒乓球赛事资讯 · 赛果/排名/赛制/场地/票价/新闻 · 国乒中国球员重点"
    og_image = (SITE_URL + BASE + "/share.svg") if SITE_URL else (BASE + "/share.svg")
    meta = f"""<meta name="description" content="{ESCAPE(og_desc)}">
<meta property="og:site_name" content="乒乓赛事资讯">
<meta property="og:title" content="{ESCAPE(og_title)}">
<meta property="og:description" content="{ESCAPE(og_desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{ESCAPE(abs_path)}">
<meta property="og:image" content="{ESCAPE(og_image)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{ESCAPE(og_title)}">
<meta name="twitter:description" content="{ESCAPE(og_desc)}">"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{ESCAPE(title)} · 乒乓赛事资讯</title>
{meta}
<link rel="stylesheet" href="{url('/styles.css')}">
</head>
<body>
<header><div class="container nav">
  <span class="brand">🏓 <span>乒乓</span>资讯</span>
  {nav_items}
  <form class="pp-search-form" style="margin-left:auto">
    <input class="pp-search" type="search" placeholder="检索本页…" aria-label="检索本页">
  </form>
</div></header>
<main class="container">
{content}
</main>
<footer class="footer">
  <div class="container">数据来源：ITTF / WTT 官方及公开渠道 · 本站为静态资讯，仅供球迷参考</div>
</footer>
<script src="{url('/app.js')}"></script>
</body>
</html>"""


def _card(title, muted, body="", badge=""):
    badge_html = f'<span class="badge {badge}">{ESCAPE(badge)}</span>' if badge else ""
    return (f'<div class="card"><h3>{ESCAPE(title)} {badge_html}</h3>'
            f'<div class="muted">{ESCAPE(muted)}</div>{body}</div>')


# ---------------------------------------------------------------------------
# 页面
# ---------------------------------------------------------------------------
def page_index(d) -> str:
    daily = d["daily"]
    headline = daily.get("headline") or "暂无今日头条"
    top_results = daily.get("top_results") or []
    names = daily.get("chinese_players", {}).get("names") or []

    result_items = ""
    for r in top_results:
        result_items += (
            f'<div class="item"><div class="t">{ESCAPE(r.get("player_a",""))} '
            f'<span style="color:var(--accent)">{ESCAPE(str(r.get("score","")))}</span> '
            f'{ESCAPE(r.get("player_b",""))} </div>'
            f'<div class="meta">{ESCAPE(r.get("round",""))} · {ESCAPE(r.get("event",""))}</div>'
            f'</div>'
        )
    if not result_items:
        result_items = '<div class="item"><div class="t">暂无重点赛果</div></div>'

    rank_tbl = _rank_table(d, limit=8)

    return f"""
<section class="hero">
  <div class="tag">今日乒乓 · {ESCAPE(d.get("daily",{}).get("date",""))}</div>
  <div class="headline"><a href="{url('/daily.html')}" style="color:inherit">{ESCAPE(headline)}</a></div>
  {f'<div class="muted">国乒在阵：{ESCAPE("、".join(names))}</div>' if names else ''}
</section>

<h2>重点赛果</h2><div class="list">{result_items}</div>

<h2>中国球员 · 世界排名</h2>
{rank_tbl}
<p style="margin-top:16px"><a href="{url('/daily.html')}">查看今日完整简报 →</a></p>
"""


def _rank_table(d, limit=None) -> str:
    ranking = d.get("ranking") or []
    if limit:
        ranking = ranking[:limit]
    rows = ""
    for r in ranking:
        name = r.get("name_zh") or r.get("name") or ""
        mv = r.get("movement") or 0
        mv_cls = "up" if mv > 0 else ("down" if mv < 0 else "")
        mv_txt = (f'(<span class="{mv_cls}">{mv:+d}</span>)' if mv != 0 else "")
        cn = "china" if r.get("country") == "CHN" else ""
        rows += (f'<tr class="{"cn" if r.get("country")=="CHN" else ""}">'
                 f'<td class="rank">{r.get("rank","")}</td>'
                 f'<td>{ESCAPE(name)}</td>'
                 f'<td>{ESCAPE(r.get("country",""))}</td>'
                 f'<td>{int(r.get("points",0)):,}</td>'
                 f'<td>{mv_txt}</td></tr>')
    if not rows:
        rows = '<tr><td colspan="5">暂无排名数据</td></tr>'
    return f"""<table><thead><tr><th>#</th><th>球员</th><th>国家</th><th>积分</th><th>变动</th></tr></thead>
    <tbody>{rows}</tbody></table>"""


def page_rankings(d) -> str:
    ranking = d.get("ranking") or []
    men = [r for r in ranking if (r.get("event") or "men") == "men"]
    women = [r for r in ranking if r.get("event") == "women"]
    # 若没有 event 区分，全部归 men 展示
    if not women:
        men = ranking
    def table(items):
        return _rank_table({"ranking": items})
    blocks = ""
    if men:
        blocks += f"<h2>男子世界排名</h2>{table(men)}"
    if women:
        blocks += f"<h2>女子世界排名</h2>{table(women)}"
    if not men and not women:
        blocks = "<p class='sub'>暂无排名数据</p>"
    return f"""<h1>世界排名</h1>
<p class="sub">数据日期：{ESCAPE(d.get("rank_date",""))} · 中国球员已高亮</p>
{blocks}"""


def page_calendar(d) -> str:
    tours = d.get("tournaments") or []
    cards = ""
    for t in tours:
        loc = (t.get("location") or {})
        loc_txt = f"{loc.get('city','')} · {loc.get('venue','') or t.get('venue_zh','')}"
        cards += _card(
            f"{t.get('name_zh') or t.get('name')}",
            f"{t.get('start_date','')} ~ {t.get('end_date','')} · {ESCAPE(loc_txt)}",
            "",
            badge=t.get("status", ""),
        )
    if not cards:
        cards = "<p class='sub'>暂无赛事数据</p>"
    return f"""<h1>赛事日历</h1>
<p class="sub">近 3 个月及未来赛事 · 含赛制、场地、票价信息</p>
<div class="grid">{cards}</div>"""


def page_tournaments(d) -> str:
    tours = d.get("tournaments") or []
    cards = ""
    for t in tours:
        fmt = (t.get("format") or {}).get("type", "")
        price = (t.get("tickets") or [{}])[0].get("price_zh", "")
        cards += (
            f'<a class="item" href="{url("/tournaments/" + t["id"] + ".html")}" style="color:inherit">'
            f'<div class="t">{ESCAPE(t.get("name_zh") or t.get("name"))}</div>'
            f'<div class="meta">{ESCAPE(t.get("level",""))} · {ESCAPE(t.get("status",""))}'
            f'{f" · {ESCAPE(fmt)}" if fmt else ""}'
            f'{f" · 票价 {ESCAPE(price)}" if price else ""}</div></a>'
        )
    if not cards:
        cards = "<p class='sub'>暂无赛事数据</p>"
    return f"""<h1>赛事</h1>
<div class="list">{cards}</div>"""


def page_tournament_detail(d, tid) -> str:
    t = _read_json(TOURNAMENTS_DIR / f"{tid}.json")
    if not t:
        return base_layout("赛事不存在",
                           f"<p>该赛事不存在。</p><p><a href='{url('/tournaments.html')}'>返回赛事列表</a></p>",
                           "tournaments.html")
    name = t.get("name_zh") or t.get("name")
    loc = t.get("location") or {}
    fmt = t.get("format") or {}
    fmt_txt = fmt.get("description_zh") or fmt.get("type") or "未提供"

    info = (f"<div class='card'><h3>赛事信息</h3>"
            f"<div class='muted'>级别：{ESCAPE(t.get('level',''))}</div>"
            f"<div class='muted'>时间：{ESCAPE(t.get('start_date',''))} ~ {ESCAPE(t.get('end_date',''))}</div>"
            f"<div class='muted'>地点：{ESCAPE(loc.get('city',''))} · {ESCAPE(loc.get('venue','') or t.get('venue_zh',''))}</div>"
            f"<div class='muted'>状态：{ESCAPE(t.get('status',''))}</div></div>")

    fmt_card = f"<div class='card'><h3>赛制</h3><div class='muted'>{ESCAPE(fmt_txt)}</div></div>"

    tickets = t.get("tickets") or []
    ticket_rows = "".join(
        f"<tr><td>{ESCAPE(tk.get('tier',''))}</td><td>{ESCAPE(tk.get('price_zh',''))}</td>"
        f"<td>{ESCAPE(tk.get('currency',''))}</td></tr>" for tk in tickets
    )
    ticket_card = (f"<div class='card'><h3>票价</h3>"
                   + (f"<table><thead><tr><th>档位</th><th>价格</th><th>币种</th></tr></thead>"
                      f"<tbody>{ticket_rows}</tbody></table>" if ticket_rows
                      else "<div class='muted'>暂无票价信息</div>")
                   + "</div>")

    # 相关赛果
    related = [m for m in (d.get("matches") or []) if m.get("tournament_id") == tid]
    rel_rows = "".join(
        f"<tr><td>{ESCAPE(m.get('round',''))}</td>"
        f"<td>{ESCAPE(m['player_a'].get('name_zh') or m['player_a'].get('name'))}</td>"
        f"<td>{ESCAPE(str(m.get('score_a','')))}:{ESCAPE(str(m.get('score_b','')))}</td>"
        f"<td>{ESCAPE(m['player_b'].get('name_zh') or m['player_b'].get('name'))}</td></tr>"
        for m in related
    )
    rel_card = ("<div class='card' style='grid-column:1/-1'><h3>相关赛果</h3>"
                + (f"<table><thead><tr><th>轮次</th><th>A</th><th>比分</th><th>B</th></tr></thead>"
                   f"<tbody>{rel_rows}</tbody></table>" if rel_rows
                   else "<div class='muted'>暂无赛果</div>")
                + "</div>")

    content = f"""<p><a href="{url('/tournaments.html')}">← 返回赛事列表</a></p>
<h1>{ESCAPE(name)}</h1>
<p class="sub">英文名：{ESCAPE(t.get('name',''))}</p>
<div class="grid">{info}{fmt_card}{ticket_card}{rel_card}</div>
<p style="margin-top:20px"><a href="{url('/calendar.html')}">查看全部赛事日历</a></p>"""
    return base_layout(name, content, "tournaments.html")


def page_news(d) -> str:
    news = d.get("news") or []
    items = ""
    for n in news:
        badge = (
            '<span class="badge china">国乒</span> '
            if n.get("is_chinese_related") else ""
        )
        items += (f'<div class="item"><div class="t">{badge}'
                  f'{ESCAPE(n.get("title",""))}</div>'
                  f'<div class="meta">{ESCAPE(n.get("source",""))} · '
                  f'{ESCAPE(n.get("published_at",""))}</div></div>')
    if not items:
        items = "<p class='sub'>暂无新闻数据</p>"
    return f"""<h1>新闻动态</h1>
<p class="sub">国际官方动态 + 中国球员相关新闻（国乒标记为绿色）</p>
<div class="list">{items}</div>"""


def build_h2h(matches: list[dict]) -> list[dict]:
    """从赛果派生双方历史交锋 H2H。仅统计 completed 的相互交手。"""
    from collections import defaultdict
    acc: dict[tuple, dict] = defaultdict(lambda: {"a": 0, "b": 0, "games": 0})
    for m in matches:
        if m.get("status") != "completed" or not m.get("winner"):
            continue
        a = m.get("player_a") or {}
        b = m.get("player_b") or {}
        aid, bid = a.get("id"), b.get("id")
        if not (aid and bid):
            continue
        key = tuple(sorted([aid, bid]))
        rec = acc[key]
        rec.setdefault("players", {aid: a, bid: b})
        rec["games"] += 1
        winner = m["player_a"] if m["winner"] == "a" else m["player_b"]
        wname = winner.get("id")
        rec[f"{'a' if wname == aid else 'b'}"] += 1
    out = []
    for key, rec in acc.items():
        aid, bid = key
        a, b = rec["players"][aid], rec["players"][bid]
        # Chinese 优先排序
        is_cn = (a.get("country") == "CHN") or (b.get("country") == "CHN")
        out.append({
            "player_a": a, "player_b": b,
            "wins_a": rec["a"], "wins_b": rec["b"], "total": rec["games"],
            "is_chinese_pair": is_cn,
        })
    out.sort(key=lambda x: (not x["is_chinese_pair"], x["total"]), reverse=True)
    return out


def page_players(d) -> str:
    players = d.get("china") or []
    cards = ""
    for p in players:
        pl = p.get("name_zh") or p.get("name")
        cards += (
            f'<a class="item" href="{url("/players/" + p["id"] + ".html")}" style="color:inherit">'
            f'<div class="t">{ESCAPE(pl)} <span class="badge china">国乒</span></div>'
            f'<div class="meta">世界第 {ESCAPE(str(p.get("world_rank", "-")))} · '
            f'{int(p.get("world_points", 0)):,} 分 · {ESCAPE(p.get("country",""))}</div></a>'
        )
    if not cards:
        cards = "<p class='sub'>暂无球员数据</p>"
    return f"""<h1>中国球员资料库</h1>
<p class="sub">世界排名、积分、冠军、近期赛果</p>
<div class="list">{cards}</div>"""


def page_player_detail(d, pid) -> str:
    p = _read_json(PLAYERS_DIR / f"{pid}.json")
    if not p:
        return base_layout("球员不存在",
                           f"<p>该球员不存在。</p><p><a href='{url('/players.html')}'>返回球员库</a></p>",
                           "players.html")
    name = p.get("name_zh") or p.get("name")
    tid_map = {t.get("id"): (t.get("name_zh") or t.get("name")) for t in (d.get("tournaments") or [])}
    titles = p.get("titles") or []
    title_txt = "、".join(
        f"{tid_map.get(t.get('tournament_id'), t.get('tournament_id') or '')} {t.get('year','')}"
        for t in titles) or "暂无"
    recent = p.get("recent_matches") or []
    rows = "".join(
        f"<tr><td>{ESCAPE(r.get('date',''))}</td><td>{ESCAPE(r.get('opponent',''))}</td>"
        f"<td>{ESCAPE(r.get('score',''))}</td><td>{'胜' if r.get('won') else '负'}</td></tr>"
        for r in recent[:8]
    )
    info = (f"<div class='card'><h3>{ESCAPE(name)}</h3>"
            f"<div class='muted'>英文名：{ESCAPE(p.get('name',''))}</div>"
            f"<div class='muted'>国家：{ESCAPE(p.get('country',''))}</div>"
            f"<div class='muted'>世界排名：{ESCAPE(str(p.get('world_rank','-')))}（{int(p.get('world_points',0)):,} 分）</div>"
            f"<div class='muted'>近3月冠军：{ESCAPE(title_txt)}</div></div>")
    recent_card = ("<div class='card' style='grid-column:1/-1'><h3>近期赛果</h3>"
                   + (f"<table><thead><tr><th>日期</th><th>对手</th><th>比分</th><th>结果</th></tr></thead>"
                      f"<tbody>{rows}</tbody></table>" if rows
                      else "<div class='muted'>暂无赛果</div>")
                   + "</div>")
    content = f"""<p><a href="{url('/players.html')}">← 返回球员库</a></p>
<div class="grid">{info}{recent_card}</div>
<p style="margin-top:20px"><a href="{url('/rankings.html')}">查看完整排名</a></p>"""
    return base_layout(name, content, "players.html")


def page_h2h(d) -> str:
    pairs = build_h2h(d.get("matches") or [])
    rows = ""
    for x in pairs:
        a = x["player_a"]["name_zh"] or x["player_a"]["name"]
        b = x["player_b"]["name_zh"] or x["player_b"]["name"]
        wa, wb = x["wins_a"], x["wins_b"]
        badge = ' <span class="badge china">国乒</span>' if x["is_chinese_pair"] else ""
        rows += (f"<tr><td>{ESCAPE(a)}</td><td>{wa} - {wb}</td>"
                 f"<td>{ESCAPE(b)}</td><td>{x['total']} 场{badge}</td></tr>")
    if not rows:
        rows = '<tr><td colspan="4">暂无交锋数据</td></tr>'
    return f"""<h1>历史交锋 (H2H)</h1>
<p class="sub">双方近3个月交手战绩，中国球员对局优先</p>
<table><thead><tr><th>球员A</th><th>A胜-B胜</th><th>球员B</th><th>场次</th></tr></thead>
<tbody>{rows}</tbody></table>"""


def page_charts(d) -> str:
    from collections import defaultdict
    history = d.get("history") or []
    if not history:
        return "<h1>排名趋势</h1><p class='sub'>暂无历史数据</p>"
    # 取前5中国球员，绘制积分折线（SVG）
    china_pts = [_read_json(PLAYERS_DIR / f"{p['id']}.json") for p in (d.get("china") or [])]
    china_pts = [p for p in china_pts if p]

    dates = [h["date"] for h in history]
    x = {dt: i for i, dt in enumerate(dates)}
    width, height = 720, 320
    pad = 40
    series_colors = ["#f5a623", "#ff6b6b", "#4ad295", "#4aa3ff", "#c07df2"]

    top = china_pts[:5]
    all_pts = [p.get("world_points") or 0 for p in top]
    # 无 world_points 时从 history 取
    lines, legend = [], []
    max_pts = 1000
    for idx, p in enumerate(top):
        pid = p["id"]
        pts_by_date = []
        for h in history:
            row = next((r for r in h["ranking"] if r.get("player_id") == pid), None)
            pts_by_date.append((row["points"] if row else 0) or 0)
        if pts_by_date:
            max_pts = max(max_pts, max(pts_by_date))
            color = series_colors[idx % len(series_colors)]
            points_svg = " ".join(
                f"{pad + x[dt] * (width - 2*pad) / max(1, len(dates)-1)},"
                f"{height - pad - (v / max(1, max_pts)) * (height - 2*pad)}"
                for dt, v in zip(dates, pts_by_date)
            )
            lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" '
                         f'points="{points_svg}"/>')
            legend.append(f'<span style="color:{color}">● {ESCAPE(p.get("name_zh") or p.get("name"))}</span>')
    if not lines:
        lines = ["<p class='sub'>暂无趋势数据</p>"]

    chart = (f'<svg viewBox="0 0 {width} {height}" style="width:100%;height:auto;background:var(--card);'
             f'border-radius:12px;border:1px solid var(--line)">{chr(10)}'
             + "".join(lines) + "</svg>")
    return f"""<h1>排名趋势</h1>
<p class="sub">中国球员世界排名积分走势（近 8 周，演示数据）</p>
<div style="margin-bottom:10px">{'  '.join(legend)}</div>
{chart}"""


def page_watch(d) -> str:
    return f"""<h1>观赛指南</h1>
<p class="sub">如何收看乒乓赛事、购票入口</p>
<div class="grid">
  <div class="card"><h3>电视/网络直播</h3><div class="muted">总台体育频道(CCTV-5)、央视频、咪咕视频、腾讯体育等渠道直播 WTT 及国乒赛事</div></div>
  <div class="card"><h3>赛事日程</h3><div class="muted">可在 <a href="{url('/calendar.html')}">赛事日历</a> 查看近期赛程</div></div>
  <div class="card"><h3>购票入口</h3><div class="muted">国内赛事票价可在各赛事详情页查看，并通过大麦、猫眼等平台购票</div></div>
  <div class="card"><h3>关注球员</h3><div class="muted">在 <a href="{url('/players.html')}">球员库</a> 查看国乒选手排名与成绩</div></div>
</div>"""


def page_daily(d, date_str: str = "") -> str:
    """今日/指定日期简报：分享落地页，聚合头条/赛果/新闻/排名。"""
    daily = d.get("daily") or {}
    if date_str:
        day = _read_json(DAILY_DIR / f"{date_str}.json") or {}
        if day:
            daily = day
    head_date = daily.get("date", date_str or "")
    headline = daily.get("headline") or "暂无简报"
    results = daily.get("top_results") or []
    result_items = "".join(
        f'<div class="item"><div class="t">{ESCAPE(r.get("player_a",""))} '
        f'<span style="color:var(--accent)">{ESCAPE(str(r.get("score","")))}</span> '
        f'{ESCAPE(r.get("player_b",""))}</div>'
        f'<div class="meta">{ESCAPE(r.get("event",""))} · {ESCAPE(r.get("round",""))}</div></div>'
        for r in results
    ) or "<p class='sub'>今日暂无重点赛果</p>"

    moves = daily.get("rankings_move") or []
    move_items = ""
    for m in moves:
        mv = m.get("movement") or 0
        mv_txt = f"({mv:+d})" if mv != 0 else ""
        move_items += (f'<div class="item"><div class="t">{ESCAPE(m.get("name",""))}</div>'
                       f'<div class="meta">第 {ESCAPE(str(m.get("rank","")))} 名{mv_txt}</div></div>')
    if not move_items:
        move_items = "<p class='sub'>暂无排名变动</p>"

    news = daily.get("top_news") or []
    news_items = "".join(
        f'<div class="item"><div class="t">{ESCAPE(n.get("title",""))}</div>'
        f'<div class="meta">{ESCAPE(n.get("source",""))}</div></div>' for n in news
    ) or "<p class='sub'>暂无新闻</p>"

    cn = daily.get("chinese_players") or {}
    names = cn.get("names") or []

    return f"""<div class="hero">
  <div class="tag">乒乓简报 · {ESCAPE(head_date)}</div>
  <div class="headline">{ESCAPE(headline)}</div>
  {f'<div class="muted">今日国乒在阵：{ESCAPE("、".join(names))}</div>' if names else ''}
</div>
<h2>重点赛果</h2><div class="list">{result_items}</div>
<h2>中国球员排名变动</h2><div class="grid">{move_items}</div>
<h2>今日新闻</h2><div class="list">{news_items}</div>
<p style="margin-top:24px"><a href="{url('/index.html')}">← 返回首页</a> ·
   <a href="{url('/rankings.html')}">完整排名</a> ·
   <a href="{url('/news.html')}">更多新闻</a></p>"""


def page_daily_archive(d) -> str:
    """归档列表：各日期简报入口。配合 daily/ 子页。"""
    items = "".join(
        f'<a class="item" href="{url("/" + x["url"])}" style="color:inherit">'
        f'<div class="t">{ESCAPE(x["date"])}</div>'
        f'<div class="meta">{ESCAPE(x.get("headline",""))}</div></a>'
        for x in (d.get("daily_list") or [])
    ) or "<p class='sub'>暂无归档</p>"
    return f"<h1>简报归档</h1><div class='list'>{items}</div>"


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def generate() -> None:
    log.info("读取数据…")
    d = load_all()
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    # 静态资源
    css_css = CSS_PATH.read_text(encoding="utf-8")
    (PUBLIC_DIR / "styles.css").write_text(css_css, encoding="utf-8")
    assets = Path(__file__).resolve().parent / "site_assets"
    for fname in ("app.js", "share.svg"):
        p = assets / fname
        if p.exists():
            (PUBLIC_DIR / fname).write_text(p.read_text(encoding="utf-8"), encoding="utf-8")

    pages = {
        "index.html": page_index(d),
        "daily.html": page_daily(d),
        "daily-archive.html": page_daily_archive(d),
        "rankings.html": page_rankings(d),
        "players.html": page_players(d),
        "calendar.html": page_calendar(d),
        "tournaments.html": page_tournaments(d),
        "h2h.html": page_h2h(d),
        "charts.html": page_charts(d),
        "news.html": page_news(d),
        "watch-guide.html": page_watch(d),
        "404.html": _page_404(),
    }

    # 每日归档详情页（daily-<date>.html）
    for x in d.get("daily_list") or []:
        pages[x["url"]] = page_daily(d, x["date"])

    # 赛事详情页
    for t in d.get("tournaments") or []:
        tid = t.get("id")
        if tid:
            pages[f"tournaments/{tid}.html"] = page_tournament_detail(d, tid)

    # 球员详情页
    for p in d.get("players") or []:
        pid = p.get("id")
        if pid and p.get("is_chinese"):
            pages[f"players/{pid}.html"] = page_player_detail(d, pid)

    def _is_detail(name: str) -> bool:
        return name.startswith(("tournaments/", "players/"))

    for name, content in pages.items():
        # 详情页已 self-contained；其余套布局
        full = content if _is_detail(name) else base_layout(
            _title_for(name), content, name)
        out = PUBLIC_DIR / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(full, encoding="utf-8")

    _write_seo_files(pages)
    log.info("生成 %d 个页面 → %s", len(pages), PUBLIC_DIR)
    print("站点已生成到:", PUBLIC_DIR)


def _write_seo_files(pages: dict[str, str]) -> None:
    """生成 robots.txt、sitemap.xml 与 .nojekyll（禁用 Jekyll 预处理）。"""
    (PUBLIC_DIR / ".nojekyll").write_text("", encoding="utf-8")
    (PUBLIC_DIR / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n", encoding="utf-8")
    locs = []
    for name in pages:
        path = BASE + "/" + name
        locs.append(SITE_URL + path if SITE_URL else path)
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
               "".join(f"<url><loc>{html.escape(l)}</loc></url>\n" for l in locs) +
               "</urlset>\n")
    (PUBLIC_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8")


def _page_404() -> str:
    return (f"<h1>404 · 页面不存在</h1><p>你访问的内容不存在或已移动。</p>"
            f"<p><a href=\"{url('/index.html')}\">返回首页</a> · "
            f"<a href=\"{url('/daily.html')}\">查看今日简报</a></p>")


def _title_for(page: str) -> str:
    base = {"index.html": "首页", "daily.html": "今日简报", "daily-archive.html": "简报归档",
            "rankings.html": "排名", "players.html": "球员",
            "calendar.html": "赛事日历", "tournaments.html": "赛事",
            "h2h.html": "历史交锋", "charts.html": "排名趋势",
            "news.html": "新闻", "watch-guide.html": "观赛指南",
            "404.html": "页面不存在"}
    if page.startswith("daily-"):
        return "乒乓简报"
    return base.get(page, "乒乓赛事资讯")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate()
