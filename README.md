# 🏓 乒乓球赛事资讯（PingPong News）

面向「跟国乒 / 中国球员」球迷的**纯静态、公开可分享**的乒乓球赛事资讯站。

- 数据由 **GitHub Actions 定时采集**，自动抓取 ITTF/WTT 国际赛事 + 国内赛事（乒超/全运会/全国锦标赛）。
- 站点由 **Python 静态生成器**生成（零外部依赖），发布到 **GitHub Pages**，生成永久公开链接。
- 每日通过**企业微信/公众号**推送「一句话摘要 + 完整页面链接」。

> 技术说明：站点层选用零依赖 Python 静态生成器（而非 Astro），因本机沙箱无外网、无法本地构建 Node 栈；产物为标准静态 HTML，效果一致（SEO 友好、GitHub Pages 直接托管）。

## 目录结构

```
pingpong-news/
├── data/                  # 采集后的结构化 JSON 数据（提交到仓库）
│   ├── tournaments/       # 赛事合集（含赛制、场地、票价、签表）
│   ├── matches/           # 比赛结果
│   ├── players/           # 中国球员资料库（由排名+赛果派生）
│   ├── rankings/          # 世界/国内排名（时间序列）
│   ├── news/              # 新闻动态
│   └── daily/             # 每日汇总
├── public/                # 站点生成产物（GitHub Pages 站点根目录）
├── scripts/               # 采集与站点生成脚本（Python）
│   ├── config.py          # 全局配置（路径、数据源端点、base、关键词）
│   ├── fetch_ittf.py      # 国际赛事采集器（ITTF/WTT，可配置端点+mock回退）
│   ├── fetch_news.py      # 新闻 + 国内赛事采集器（mock回退）
│   ├── standardize.py     # 数据标准化 & 去重 & 校验 & 球员派生
│   ├── build_daily.py     # 每日汇总生成
│   ├── generate_site.py   # 静态站点生成器（HTML 页面 + sitemap/robots）
│   ├── push_wechat.py     # 企业微信每日推送
│   ├── validate.py        # 数据质量校验（CI 大声失败）
│   ├── serve.py           # 本地预览服务器
│   └── main.py            # 一键运行完整数据管道
├── .github/workflows/
│   └── data-pipeline.yml  # 定时采集 + 站点生成 + Pages 发布
└── requirements.txt
```

## 数据模型

见 [`data/SCHEMA.md`](data/SCHEMA.md)。

## 采集频率（分层）

| 层 | 内容 | 频率 |
|---|---|---|
| 国际赛事 | WTT/奥运/世乒赛/世界杯：赛果、排名、积分、签表 | 实时（GH Actions cron，每30分钟） |
| 国内赛事 | 乒超/全运会/全国锦标赛：赛果、场地、票价 | 日更（抓取+人工核实） |
| 新闻 | 赛果动态 + 中文新闻 | 实时 |

## 本地验证（无外网）

本地运行演示数据链路（mock）：

```
cd scripts
python main.py --mock              # 采集+标准化+每日汇总
python generate_site.py            # 生成站点到 public/
```

## 部署配置（GitHub Pages）

仓库 → Settings → Pages → Source 选择 **GitHub Actions**。可选 Variables/Secrets：
- `PP_BASE`：项目站设为 `/仓库名`（用户站/自定义域名留空）
- `PP_SHARE_URL`：每日推送的完整站点链接
- `PP_USE_MOCK=1`：先用演示数据跑（默认关，真实采集）

