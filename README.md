# ReachALL — 推广情报中台

EasyClaw 社媒推广辅助系统。实时聚合国内主流平台热榜，并通过 MiniMax LLM 一键生成 EasyClaw 推广内容。

---

## 项目是什么

面向 EasyClaw 产品推广团队的内部工具。核心功能：

1. **热榜监控** — 实时抓取微博、抖音、B站、V2EX、小红书的热点话题，展示热度、排名
2. **AI 推文生成** — 选中任意热点 → 选目标平台 + 语气风格 → 调 MiniMax M2.7 生成推广文案
3. **推文库** — 保存历史生成记录，方便回顾和复用

---

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | 单文件 `index.html`（原生 HTML/CSS/JS，无构建工具） |
| 后端 | Python + FastAPI，运行在 `localhost:8765` |
| 数据抓取 | 直接调各平台公开 API；V2EX 走 `agent-reach` 库 |
| LLM | MiniMax M2.7（`https://api.minimaxi.com/v1/chat/completions`） |
| 进程管理 | `start.sh` + `nohup` + `.server.pid` |

---

## 目录结构

```
ReachALL/
├── index.html        # 前端单页应用
├── server.py         # FastAPI 后端（数据聚合 + LLM 生成）
├── start.sh          # 后端进程管理脚本
├── .server.pid       # 后台进程 PID（运行时自动生成）
└── .server.log       # 后台日志（运行时自动生成）
```

外部依赖（不在项目目录内）：

```
~/.agent-reach/
├── config.yaml           # Twitter 等平台的 API token
└── xhs-cookies.json      # 小红书登录 cookie（需手动更新）

~/.hermes/.env            # MiniMax API key 存放位置（server.py 中硬编码使用）
~/.local/pipx/venvs/agent-reach/  # agent-reach Python 环境
```

---

## 启动方式

```bash
# 后台启动（推荐）
./start.sh start

# 查看状态
./start.sh status

# 停止
./start.sh stop

# 重启
./start.sh restart

# 前台启动（看实时日志）
./start.sh
```

后端启动后，直接用浏览器打开 `index.html` 即可使用（无需 web server，本地文件直接打开）。

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/trends` | 全平台热榜，可传 `?platform=weibo\|bilibili\|douyin\|v2ex\|xhs\|all` |
| GET | `/api/trends/{name}` | 单平台热榜 |
| POST | `/api/generate` | 生成推文，见下方 payload |
| POST | `/api/cache/clear` | 清除 5 分钟缓存，强制刷新 |
| GET | `/api/health` | 服务健康状态 |

`/api/generate` 请求体：

```json
{
  "topic_title": "歌手AI海报",
  "topic_heat": "115万",
  "topic_platform": "weibo",
  "target_platform": "weibo",
  "tone": "营销种草",
  "extra": ""
}
```

`target_platform` 可选值：`weibo` / `douyin` / `xhs` / `bilibili` / `v2ex`

`tone` 可选值：`营销种草` / `专业干货` / `轻松幽默` / `情感共鸣`

---

## 数据来源说明

| 平台 | 接口 | 备注 |
|------|------|------|
| 微博 | `weibo.com/ajax/side/hotSearch` | 无需认证，实时 |
| 抖音 | `iesdouyin.com` 热搜榜 | 无需认证 |
| B站 | `api.bilibili.com` 排行榜 | 无需认证 |
| V2EX | agent-reach `V2EXChannel` | 需要 `agent-reach` 安装 |
| 小红书 | 搜索 API | **需要登录 cookie**，反爬严格，500 时需更新 cookie |

---

## 更新小红书 Cookie

小红书 cookie 有效期短，出现 500 错误时需要手动更新：

1. 浏览器登录小红书，打开 DevTools → Application → Cookies
2. 找到 `web_session` 和 `id_token` 两个值
3. 更新 `~/.agent-reach/xhs-cookies.json`：

```json
[
  {"name": "web_session", "value": "你的值", "domain": ".xiaohongshu.com", "path": "/", "expires": -1, "size": 49, "httpOnly": false, "secure": false, "session": true, "sameSite": "Lax"},
  {"name": "id_token",    "value": "你的值", "domain": ".xiaohongshu.com", "path": "/", "expires": -1, "size": 144, "httpOnly": false, "secure": false, "session": true, "sameSite": "Lax"}
]
```

4. `./start.sh restart` 重启后端

---

## 缓存策略

各平台数据缓存 5 分钟（`CACHE_TTL = 300`），避免频繁请求被封。
可通过 `POST /api/cache/clear` 或 `./start.sh restart` 强制刷新。

---

## 后续计划

- [ ] 小红书签名算法（`x-s`）支持，绕过反爬
- [ ] Twitter/X 热搜接入（`~/.agent-reach/config.yaml` 已有 token）
- [ ] 推文库持久化（目前仅 localStorage）
- [ ] 多产品支持（当前 system prompt 写死为 EasyClaw）
- [ ] SDK/API 输出层，支持第三方平台消费数据
