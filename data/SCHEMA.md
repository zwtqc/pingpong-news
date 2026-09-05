# 数据模型定义（SCHEMA）

所有采集数据以结构化 JSON 存储于 `data/` 下，字段统一遵循以下定义。字段名保持 snake_case，值为 ASCII 时用英文，展示文本用 `*_zh` 中文字段。

---

## 1. 赛事 tournament `data/tournaments/<id>.json`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 唯一 ID，如 `wtt-grand-smash-2026-02` |
| `name` | string | 官方赛事名（英文） |
| `name_zh` | string | 中文名 |
| `level` | string | `grand_smash` / `champions` / `star_contender` / `contender` / `olympic` / `world_championship` / `world_cup` / `china_super_league` / `national_games` / `national_championship` / `other` |
| `category` | string | `international` / `domestic` |
| `start_date` | string | `YYYY-MM-DD` |
| `end_date` | string | `YYYY-MM-DD` |
| `location` | object | `{ city, country, venue }`，`venue` 为场馆名 |
| `venue_zh` | string | 场馆中文名（含地址） |
| `format` | object | 赛制：`{ type: "single_elimination"|"round_robin"|"group+elimination", doubles: bool, best_of: {men, women}, main_draw_size, description_zh }` |
| `tickets` | array | 票价：`[ { tier: "首轮", price_zh: "¥100起", currency: "CNY", min, max, buy_url, note } ]` |
| `status` | string | `upcoming` / `ongoing` / `completed` |
| `draws` | object | 签表（可选）：`{ men: [...], women: [...], mixed_doubles: [...] }` 每个为签位节点列表 |
| `updated_at` | string | ISO 时间 |

---

## 2. 球员 player `data/players/<id>.json`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 唯一 ID，如 `fan-zhendong` |
| `name` | string | 英文名 |
| `name_zh` | string | 中文名 |
| `country` | string | 国家代码，如 `CHN` |
| `is_chinese` | bool | 是否中国球员（重点） |
| `birth_date` | string | 出生日期 |
| `world_rank` | int | 当前世界排名 |
| `world_points` | int | 当前世界排名积分 |
| `style` | string | 打法，如 `right-shakehand` / `left-penhold` |
| `hand` | string | `right` / `left` |
| `grip` | string | `shakehand` / `penhold` |
| `titles` | array | 冠军：`[ { tournament_zh, year, level } ]` |
| `photo_url` | string | 头像 |

---

## 3. 比赛 match `data/matches/<id>.json`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 唯一 ID |
| `tournament_id` | string | 关联赛事 |
| `event` | string | `men_singles` / `women_singles` / `men_doubles` / `women_doubles` / `mixed_doubles` |
| `round` | string | 轮次，如 `final` / `semi_final` / `quarter_final` / `round_of_16` |
| `player_a` | object | `{ id, name, name_zh, country }` |
| `player_b` | object | `{ id, name, name_zh, country }` |
| `score_a` | int | 大比分 A 方 |
| `score_b` | int | 大比分 B 方 |
| `games` | array | 逐局：`[ { a: 11, b: 8 } ]`（可选） |
| `winner` | string | `a` / `b` |
| `match_date` | string | `YYYY-MM-DD` |
| `status` | string | `completed` / `live` / `scheduled` |
| `has_chinese_player` | bool | 是否有中国球员（重点筛选） |

---

## 4. 排名 ranking（时间序列）

- 单期：`data/rankings/world-<rank_date>.json`，`rank_date` 为 `YYYY-MM-DD`
- 全量聚合：`data/rankings/history.json`

每条记录：

| 字段 | 类型 | 说明 |
|---|---|---|
| `rank` | int | 名次 |
| `player_id` | string | 球员 ID |
| `name_zh` | string | 中文名 |
| `country` | string | 国家代码 |
| `points` | int | 积分 |
| `movement` | int | 较上期变动（±） |

---

## 5. 新闻 news `data/news/<id>.json`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 唯一 ID |
| `title` | string | 标题 |
| `source` | string | 来源，如 `ITTF` / `WTT` / `新浪体育` |
| `url` | string | 原文链接 |
| `published_at` | string | ISO 时间 |
| `category` | string | `result` / `official` / `player_news` / `media` |
| `summary_zh` | string | 中文摘要 |
| `is_chinese_related` | bool | 是否与中国球员相关 |

---

## 6. 每日汇总 daily `data/daily/<YYYY-MM-DD>.json`

| 字段 | 类型 | 说明 |
|---|---|---|
| `date` | string | 日期 |
| `headline` | string | 一句话头条 |
| `top_results` | array | 当日重点赛果（含中国球员优先） |
| `top_news` | array | 当日重点新闻 |
| `chinese_players` | object | 当日中国球员表现摘要 |
| `rankings_move` | array | 当日排名变动 |
| `share_url` | string | 完整站点对应页面链接 |
