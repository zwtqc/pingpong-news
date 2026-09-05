# -*- coding: utf-8 -*-
"""本地预览服务器：http://127.0.0.1:8888 浏览生成的站点。

用法：
    python scripts/serve.py        # 启动并停留在前台
"""
from __future__ import annotations

import functools
import http.server
import socketserver
from config import ROOT

PUBLIC_DIR = ROOT / "public"
PORT = 8888


def main() -> None:
    if not PUBLIC_DIR.exists():
        print("未找到 public/，请先运行: python scripts/generate_site.py")
        return
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=str(PUBLIC_DIR),
    )
    with socketserver.TCPServer(("127.0.0.1", PORT), handler) as httpd:
        print(f"乒乓赛事资讯预览： http://127.0.0.1:{PORT}/")
        print("按 Ctrl+C 停止。")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n已停止。")


if __name__ == "__main__":
    main()
