# -*- coding: utf-8 -*-
"""企业微信 Webhook 推送：把每日汇总发送到微信群/机器人。

配置：环境变量 WECHAT_WEBHOOK（企业微信机器人 webhook 地址，含 key）。
用法：
    python scripts/push_wechat.py               # 推送今日汇总（取最新 daily）
    python scripts/push_wechat.py --test        # 发送一条测试消息
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import datetime
from pathlib import Path

from config import DAILY_DIR, ROOT

log = logging.getLogger("push_wechat")

WEBHOOK_URL = os.environ.get("WECHAT_WEBHOOK", "")
SHARE_URL = os.environ.get("PP_SHARE_URL", "")


def _latest_daily() -> dict:
    if not DAILY_DIR.exists():
        return {}
    files = sorted(DAILY_DIR.glob("*.json"))
    if not files:
        return {}
    try:
        return json.loads(files[-1].read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def build_message(daily: dict) -> str:
    """把每日汇总整理成企业微信 markdown 消息。"""
    date = daily.get("date", datetime.now().date().isoformat())
    lines = [f"# 🏓 乒乓球每日简报（{date}）", ""]
    headline = daily.get("headline") or "暂无今日头条"
    lines.append(f"**头条**：{headline}")

    results = daily.get("top_results") or []
    if results:
        lines.extend(["", "**今日重点赛果**："])
        for r in results:
            lines.append(
                f"- {r.get('player_a','')} **{r.get('score','')}** {r.get('player_b','')}"
                f"（{r.get('event','')} · {r.get('round','')}）"
            )

    cn = daily.get("chinese_players") or {}
    names = cn.get("names") or []
    if names:
        lines.extend(["", f"**今日国乒在阵**：{'、'.join(names)}"])

    moves = daily.get("rankings_move") or []
    if moves:
        mv = "、".join(
            f"{m['name']} {m['rank']}名" +
            (f"({m['movement']:+d})" if (m.get('movement') or 0) != 0 else "")
            for m in moves
        )
        lines.extend(["", f"**排名**：{mv}"])

    news = daily.get("top_news") or []
    if news:
        lines.extend(["", "**今日新闻**："])
        for n in news:
            lines.append(f"- [{n.get('source','')}] {n.get('title','')}")

    share = daily.get("share_url") or SHARE_URL
    if share:
        lines.extend(["", f"👉 [查看完整图文]({share})"])
    return "\n".join(lines)


def send(content: str) -> bool:
    if not WEBHOOK_URL:
        log.warning("未配置 WECHAT_WEBHOOK，跳过推送")
        return False
    payload = json.dumps({"msgtype": "markdown", "markdown": {"content": content}},
                         ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        WEBHOOK_URL, data=payload,
        headers={"Content-Type": "application/json;charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            ok = body.get("errcode") == 0
            log.info("企业微信推送 %s: %s", "成功" if ok else "失败", body)
            return ok
    except Exception as exc:  # noqa: BLE001
        log.error("企业微信推送异常: %s", exc)
        return False


def main() -> int:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true", help="发送测试消息")
    args = p.parse_args()
    if args.test:
        return 0 if send("# 🏓 测试消息\n乒乓资讯推送链路正常 ✅") else 1
    daily = _latest_daily()
    if not daily:
        log.warning("没有可推送的每日汇总")
        return 1
    return 0 if send(build_message(daily)) else 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    raise SystemExit(main())
