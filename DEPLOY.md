# 🚀 部署上线指南

本指南带你把这个项目发布为**公开、可分享的链接**。所有采集与站点生成都在 **GitHub Actions** 完成，无需服务器。

---

## 前置
- 一个 GitHub 账号
- 本机已安装 git（本项目已在本地 `D:\1.工作文档\pingpong-news`）

---

## 步骤 1：创建 GitHub 仓库并推送

在 GitHub 上新建一个仓库（如 `pingpong-news`），然后在本地：

```powershell
cd D:\1.工作文档\pingpong-news
git init
git add .
git commit -m "初始化乒乓赛事资讯项目"
git branch -M main
git remote add origin https://github.com/<你的用户名>/pingpong-news.git
git push -u origin main
```

## 步骤 2：开启 GitHub Pages（Source 选 GitHub Actions）

仓库 → **Settings → Pages** → Source 选择 **GitHub Actions**。
之后每次 `data-pipeline.yml` 运行，都会把 `public/` 自动发布为 Pages。

## 步骤 3：配置仓库 Variables / Secrets

仓库 → **Settings → Secrets and variables → Actions**：

**Variables（仓库变量 `Variables`）**
| 变量 | 作用 | 示例 |
|---|---|---|
| `PP_BASE` | 站点路径前缀 | 项目站：`/pingpong-news`；用户站/自定义域名：留空 |
| `PP_SITE_URL` | 站点完整 URL（用于 sitemap 绝对链接） | `https://<用户名>.github.io/pingpong-news` |
| `PP_SHARE_URL` | 每日推送中的完整链接 | `https://<用户名>.github.io/pingpong-news/` |

**Secrets（密钥 `Secrets`）**
| 密钥 | 作用 |
|---|---|
| `WECHAT_WEBHOOK` | 企业微信机器人 webhook 地址（含 `?key=...`）。配置后自动推送每日简报 |
| `PP_USE_MOCK` | 设 `1` 则用演示数据（先跑通再切真实采集） |

> 真实采集默认关闭 mock（自动抓取 ITTF/WTT）。首次真实抓取若接口变动，请调整 `scripts/config.py` 中的端点。

## 步骤 4：验证

- Actions 页看 `数据管道与站点发布` 是否运行成功。
- 打开 `https://<用户名>.github.io/pingpong-news/` 确认 18 个页面可访问、数据更新。
- 配置企业微信机器人后，每日会收到包含头条、重点赛果、国乒名单、排名、链接的简报。

---

## 每日/每小时自动运行

Workflow `.github/workflows/data-pipeline.yml` 已配置：
- 每 30 分钟采集国际赛事（1 小时时效的来源）
- 生成站点 → 发布 Pages
- 发送企业微信推送（若配了 Webhook）

可随时在 Actions 页面手点 **Run workflow** 手动触发。

---

## 本地验证（可选，无外网）

```powershell
cd scripts
python main.py --mock      # 采集+标准化+每日汇总（演示数据）
python generate_site.py    # 生成 public/ 站点
```
