# -*- coding: utf-8 -*-
"""全局配置：路径、数据源、采集频率。

集中管理，方便在 GitHub Actions 与本地之间切换。
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TOURNAMENTS_DIR = DATA_DIR / "tournaments"
MATCHES_DIR = DATA_DIR / "matches"
PLAYERS_DIR = DATA_DIR / "players"
RANKINGS_DIR = DATA_DIR / "rankings"
NEWS_DIR = DATA_DIR / "news"
DAILY_DIR = DATA_DIR / "daily"

# 采集窗口：最近 3 个月
RECENT_DAYS = 90

# 站点 base 前缀（GitHub Pages 项目站需设为 "/<仓库名>"，如 "/pingpong-news"；
# 用户站/自定义域名用空字符串 "")
BASE = os.environ.get("PP_BASE", "").rstrip("/")

# 站点完整 URL（用于 sitemap 绝对链接），如 "https://<用户>.github.io/pingpong-news"
SITE_URL = os.environ.get("PP_SITE_URL", "").rstrip("/")

# ---------------------------------------------------------------------------
# 数据源配置
# ---------------------------------------------------------------------------
# 说明：ITTF / WTT 官方未公开正式文档，接口为逆向而来且可能变动。
# 这里采用「可配置端点 + 容错解析」，优先尝试官方站点数据层。
# 端点在 GitHub Actions 环境（有外网）可实测；本地沙箱无外网，用 mock 模式验证。
USE_MOCK = os.environ.get("PP_USE_MOCK", "0") == "1"

SOURCE_CONFIG = {
    "ittf": {
        # 候选端点，按顺序尝试；返回结构不同则进入标准化适配
        "base_url": os.environ.get("ITTF_BASE", "https://www.ittf.com"),
        # 赛果/赛事列表（不同站点结构差异大，这里给出常用路径）
        "calendar_path": "/_api/events",          # 事件/赛程日历
        "results_path": "/_api/results",          # 赛果
        "ranking_path": "/_api/world-ranking",    # 世界排名
        "timeout": 30,
    },
    "wtt": {
        "base_url": os.environ.get("WTT_BASE", "https://worldtabletennis.com"),
        # WTT 官网 data 层候选
        "api_path": "/api",                       # 站内数据接口（需实测确认）
        "timeout": 30,
    },
    "news": {
        # 国内主流体育媒体 RSS/新闻源（新浪/腾讯/网易体育）
        "sources": [
            {"name": "新浪体育", "url": "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&num=30"},
        ],
        "timeout": 30,
    },
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# 中文球员关键词，用于标记「中国球员相关」
CHINESE_PLAYER_KEYWORDS = [
    "樊振东", "马龙", "王楚钦", "林高远", "梁靖崑", "林诗栋", "徐昕", "高远",
    "孙颖莎", "陈梦", "王曼昱", "陈幸同", "王艺迪", "钱天一", "张瑞",
    "Fan Zhendong", "Ma Long", "Wang Chuqin", "Lin Gaoyuan", "Liang Jingkun",
    "Sun Yingsha", "Chen Meng", "Wang Manyu", "Chen Xingtong", "Wang Yidi",
]


def ensure_dirs() -> None:
    for d in (TOURNAMENTS_DIR, MATCHES_DIR, PLAYERS_DIR,
              RANKINGS_DIR, NEWS_DIR, DAILY_DIR):
        d.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    ensure_dirs()
    print("数据目录: ", DATA_DIR)
    print("USE_MOCK:", USE_MOCK)
