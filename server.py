#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReachALL 后端代理服务
调用 agent-reach channel 模块，聚合各平台热榜数据，暴露给前端。

启动: ./start.sh  或  python server.py
端口: 8765
"""

import asyncio
import http.cookiejar
import json
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.parse import quote

# ── FastAPI ──────────────────────────────────────────────────────────────────
try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
except ImportError:
    print("FastAPI not found. Run: python -m pip install fastapi uvicorn", file=sys.stderr)
    sys.exit(1)

# ── agent-reach channels ──────────────────────────────────────────────────────
AGENT_REACH_LIB = Path.home() / ".local/pipx/venvs/agent-reach/lib"
_venv_lib = next(AGENT_REACH_LIB.glob("python*/site-packages"), None)
if _venv_lib and str(_venv_lib) not in sys.path:
    sys.path.insert(0, str(_venv_lib))

try:
    from agent_reach.channels.v2ex import V2EXChannel
    from agent_reach.channels.xueqiu import XueqiuChannel
    HAS_AGENT_REACH = True
except ImportError:
    HAS_AGENT_REACH = False
    print("Warning: agent_reach not found in path", file=sys.stderr)

# ── Config ────────────────────────────────────────────────────────────────────
AGENT_REACH_DIR = Path.home() / ".agent-reach"
XHS_COOKIES_FILE = AGENT_REACH_DIR / "xhs-cookies.json"

_UA_DESKTOP = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
_UA_MOBILE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
)
TIMEOUT = 10

# ── Simple in-memory cache ────────────────────────────────────────────────────
_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 5 * 60  # 5 minutes


def cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry and time.time() - entry[0] < CACHE_TTL:
        return entry[1]
    return None


def cache_set(key: str, value: Any) -> None:
    _cache[key] = (time.time(), value)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _fetch_json(url: str, headers: dict = None, opener=None) -> Any:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": _UA_DESKTOP})
    fetcher = opener.open if opener else urllib.request.urlopen
    with fetcher(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _format_heat(n: int | None) -> str:
    if not n:
        return "—"
    if n >= 100_000_000:
        return f"{n/100_000_000:.1f}亿"
    if n >= 10_000:
        return f"{n/10_000:.0f}万"
    return str(n)


# ── Platform fetchers ─────────────────────────────────────────────────────────

def fetch_weibo() -> list[dict]:
    """微博实时热搜榜"""
    cached = cache_get("weibo")
    if cached:
        return cached

    try:
        data = _fetch_json(
            "https://weibo.com/ajax/side/hotSearch",
            headers={"Referer": "https://weibo.com", "User-Agent": _UA_DESKTOP},
        )
        items = data.get("data", {}).get("realtime", [])
        result = []
        for i, item in enumerate(items[:25]):
            title = item.get("note") or item.get("word", "")
            if not title:
                continue
            heat = item.get("num", 0)
            category = item.get("category", "")
            result.append({
                "id": f"wb_{i}",
                "platform": "weibo",
                "rank": i + 1,
                "title": title,
                "heat": heat,
                "heatLabel": _format_heat(heat),
                "category": category,
                "url": f"https://s.weibo.com/weibo?q={quote(title)}",
            })
        cache_set("weibo", result)
        return result
    except Exception as e:
        print(f"[weibo] error: {e}", file=sys.stderr)
        return []


def fetch_bilibili() -> list[dict]:
    """B站热门视频榜"""
    cached = cache_get("bilibili")
    if cached:
        return cached

    try:
        data = _fetch_json(
            "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all",
            headers={"User-Agent": _UA_DESKTOP, "Referer": "https://www.bilibili.com"},
        )
        items = data.get("data", {}).get("list", [])
        result = []
        for i, item in enumerate(items[:20]):
            stat = item.get("stat", {})
            view = stat.get("view", 0)
            result.append({
                "id": f"bili_{i}",
                "platform": "bilibili",
                "rank": i + 1,
                "title": item.get("title", ""),
                "heat": view,
                "heatLabel": _format_heat(view),
                "category": item.get("tname", ""),
                "url": f"https://www.bilibili.com/video/{item.get('bvid','')}",
                "author": item.get("owner", {}).get("name", ""),
            })
        cache_set("bilibili", result)
        return result
    except Exception as e:
        print(f"[bilibili] error: {e}", file=sys.stderr)
        return []


def fetch_douyin() -> list[dict]:
    """抖音热点榜"""
    cached = cache_get("douyin")
    if cached:
        return cached

    try:
        data = _fetch_json(
            "https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/",
            headers={"User-Agent": _UA_MOBILE, "Referer": "https://www.douyin.com"},
        )
        items = data.get("word_list", [])
        result = []
        for i, item in enumerate(items[:20]):
            heat = item.get("hot_value", 0)
            result.append({
                "id": f"dy_{i}",
                "platform": "douyin",
                "rank": i + 1,
                "title": item.get("word", ""),
                "heat": heat,
                "heatLabel": _format_heat(heat),
                "category": item.get("sentence_tag", ""),
                "url": f"https://www.douyin.com/search/{quote(item.get('word',''))}",
            })
        cache_set("douyin", result)
        return result
    except Exception as e:
        print(f"[douyin] error: {e}", file=sys.stderr)
        return []


def fetch_v2ex() -> list[dict]:
    """V2EX 热门帖子"""
    cached = cache_get("v2ex")
    if cached:
        return cached

    if not HAS_AGENT_REACH:
        return []

    try:
        ch = V2EXChannel()
        # 合并热门 + tech/programmer/ai 节点
        hot = ch.get_hot_topics(15)
        tech = ch.get_node_topics("tech", 8)
        programmer = ch.get_node_topics("programmer", 8)

        seen = set()
        combined = []
        for item in hot + tech + programmer:
            if item["id"] not in seen:
                seen.add(item["id"])
                combined.append(item)

        result = []
        for i, item in enumerate(combined[:25]):
            replies = item.get("replies", 0)
            result.append({
                "id": f"v2ex_{item['id']}",
                "platform": "v2ex",
                "rank": i + 1,
                "title": item.get("title", ""),
                "heat": replies * 1000,  # 用回复数换算热度
                "heatLabel": f"{replies} 回复",
                "category": item.get("node_title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
            })
        cache_set("v2ex", result)
        return result
    except Exception as e:
        print(f"[v2ex] error: {e}", file=sys.stderr)
        return []


def fetch_xhs() -> list[dict]:
    """小红书热门搜索（用 cookie + 搜索 AI/工具关键词）"""
    cached = cache_get("xhs")
    if cached:
        return cached

    try:
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

        if XHS_COOKIES_FILE.exists():
            cookies = json.loads(XHS_COOKIES_FILE.read_text())
            for c in cookies:
                cookie = http.cookiejar.Cookie(
                    version=0, name=c["name"], value=c["value"],
                    port=None, port_specified=False,
                    domain=".xiaohongshu.com", domain_specified=True,
                    domain_initial_dot=True, path="/", path_specified=True,
                    secure=False, expires=None, discard=True,
                    comment=None, comment_url=None, rest={}
                )
                jar.set_cookie(cookie)

        keywords = ["AI工具", "AI自动化", "AI办公", "效率工具"]
        result = []
        rank = 1

        for kw in keywords[:2]:  # 限制请求数量
            url = (
                "https://www.xiaohongshu.com/api/sns/web/v1/search/notes"
                f"?keyword={quote(kw)}&page=1&page_size=8&sort=hot&note_type=0"
            )
            req = urllib.request.Request(url, headers={
                "User-Agent": _UA_DESKTOP,
                "Referer": "https://www.xiaohongshu.com",
                "Accept": "application/json",
            })
            try:
                with opener.open(req, timeout=TIMEOUT) as r:
                    data = json.loads(r.read().decode("utf-8"))
                    items = data.get("data", {}).get("items", [])
                    for item in items:
                        note = item.get("note_card") or item
                        title = note.get("display_title") or note.get("title") or ""
                        if not title:
                            continue
                        interact = note.get("interact_info") or {}
                        likes = interact.get("liked_count", "0")
                        try:
                            heat = int(str(likes).replace("万", "0000").replace("+", ""))
                        except Exception:
                            heat = 0
                        note_id = note.get("note_id") or item.get("id", "")
                        result.append({
                            "id": f"xhs_{note_id}",
                            "platform": "xhs",
                            "rank": rank,
                            "title": title,
                            "heat": heat,
                            "heatLabel": f"{likes} 赞",
                            "category": kw,
                            "url": f"https://www.xiaohongshu.com/explore/{note_id}",
                        })
                        rank += 1
            except Exception as inner_e:
                print(f"[xhs] keyword={kw} error: {inner_e}", file=sys.stderr)

        cache_set("xhs", result)
        return result
    except Exception as e:
        print(f"[xhs] error: {e}", file=sys.stderr)
        return []


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="ReachALL API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

executor = ThreadPoolExecutor(max_workers=6)


async def run_in_thread(fn):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, fn)


# ── LLM: MiniMax ──────────────────────────────────────────────────────────────
MINIMAX_KEY = "sk-cp-UeAsUVnn0oFByLJjHCI3bUFLU4_t69n3nqvRshLiY1BePgzxNVUI2ThqZmgfSzha1SMVnWJjwP91SJ1Cnbtbtse5mq3BZPGnm2LQGlrR_5DWT7zpuLoLsKA"
MINIMAX_URL = "https://api.minimaxi.com/v1/chat/completions"
MINIMAX_MODEL = "MiniMax-M2.7"

PLATFORM_GUIDES = {
    "weibo":    {"name": "微博",   "max_len": 140, "style": "简洁有力，结尾加2-3个话题标签 #话题#"},
    "douyin":   {"name": "抖音",   "max_len": 150, "style": "开头直接抓眼球，口语化，引发互动，结尾5个话题标签"},
    "xhs":      {"name": "小红书", "max_len": 500, "style": "种草感强，真实分享语气，多用emoji，末尾6个话题标签"},
    "bilibili": {"name": "B站",    "max_len": 200, "style": "二次元/科技向，有趣有深度，结尾@相关UP主方向"},
    "v2ex":     {"name": "V2EX",  "max_len": 300, "style": "技术社区，干货为主，理性客观，程序员视角"},
}

TONE_GUIDES = {
    "营销种草": "以自然种草的口吻推广产品，让人有想下载的冲动，避免硬广感",
    "专业干货": "以专业技术视角分析，有数据、有逻辑、有见解",
    "轻松幽默": "用幽默、自嘲或反差感切入，让人会心一笑后记住产品",
    "情感共鸣": "触达打工人的真实痛点和情感，引发共鸣后自然带出产品",
}

SYSTEM_PROMPT = """你是 EasyClaw 的社媒内容运营专家。
EasyClaw 是猎豹移动出品的桌面 AI Agent 工具，基于 OpenClaw 框架：
- 无代码零配置，Mac/Windows 一键安装
- 本地沙盒运行，数据不上传
- 通过微信/飞书/WhatsApp 远程控制电脑
- 自动化处理文件、内容发布、日程管理等重复工作
- 竞品：n8n、Zapier、Dify，但更简单易用

你的任务：根据当前热点话题，为指定平台创作一条高质量推广内容，将 EasyClaw 的价值自然融入热点。
要求：真实、自然、不硬广，符合各平台的内容生态。只输出正文内容，不要加任何前缀或解释。"""


def call_minimax(prompt: str, max_tokens: int = 600) -> str:
    """调用 MiniMax API 生成文本"""
    payload = json.dumps({
        "model": MINIMAX_MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
    }, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        MINIMAX_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MINIMAX_KEY}",
        }
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"].strip()
        # 过滤 <think>...</think> 推理过程（DeepSeek/MiniMax-M2.7 会输出）
        import re
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        return text


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/trends")
async def get_trends(platform: str = "all"):
    """
    获取所有平台热榜，合并排序返回。
    ?platform=all|weibo|bilibili|douyin|v2ex|xhs
    """
    tasks = []

    if platform in ("all", "weibo"):
        tasks.append(run_in_thread(fetch_weibo))
    if platform in ("all", "bilibili"):
        tasks.append(run_in_thread(fetch_bilibili))
    if platform in ("all", "douyin"):
        tasks.append(run_in_thread(fetch_douyin))
    if platform in ("all", "v2ex"):
        tasks.append(run_in_thread(fetch_v2ex))
    if platform in ("all", "xhs"):
        tasks.append(run_in_thread(fetch_xhs))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items = []
    source_stats = {}
    for res in results:
        if isinstance(res, Exception):
            print(f"[trends] gather error: {res}", file=sys.stderr)
            continue
        if res:
            plat = res[0]["platform"] if res else "unknown"
            source_stats[plat] = len(res)
            all_items.extend(res)

    return JSONResponse({
        "ok": True,
        "total": len(all_items),
        "sources": source_stats,
        "updated_at": int(time.time()),
        "items": all_items,
    })


@app.get("/api/trends/{platform_name}")
async def get_platform_trends(platform_name: str):
    """获取单个平台热榜"""
    fetchers = {
        "weibo": fetch_weibo,
        "bilibili": fetch_bilibili,
        "douyin": fetch_douyin,
        "v2ex": fetch_v2ex,
        "xhs": fetch_xhs,
    }
    fn = fetchers.get(platform_name)
    if not fn:
        return JSONResponse({"ok": False, "error": f"Unknown platform: {platform_name}"}, status_code=404)

    items = await run_in_thread(fn)
    return JSONResponse({"ok": True, "platform": platform_name, "items": items})


class GenerateRequest(BaseModel):
    topic_title: str
    topic_heat: str = ""
    topic_platform: str = "weibo"
    target_platform: str = "weibo"
    tone: str = "营销种草"
    extra: str = ""


@app.post("/api/generate")
async def generate_post(req: GenerateRequest):
    """调用 MiniMax 基于热点生成推文"""
    plat_guide = PLATFORM_GUIDES.get(req.target_platform, PLATFORM_GUIDES["weibo"])
    tone_guide = TONE_GUIDES.get(req.tone, TONE_GUIDES["营销种草"])

    prompt = f"""当前热点话题：「{req.topic_title}」（热度：{req.topic_heat}）
来源平台：{req.topic_platform}
目标发布平台：{plat_guide['name']}
字数要求：不超过 {plat_guide['max_len']} 字
平台风格：{plat_guide['style']}
内容语气：{tone_guide}
{"额外要求：" + req.extra if req.extra else ""}

请为 EasyClaw 创作一条紧扣热点、自然植入的{plat_guide['name']}推广内容。"""

    try:
        text = await run_in_thread(lambda: call_minimax(prompt))
        return JSONResponse({"ok": True, "text": text, "model": MINIMAX_MODEL})
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        return JSONResponse({"ok": False, "error": f"MiniMax API error {e.code}: {body}"}, status_code=502)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/cache/clear")
async def clear_cache():
    """清除缓存，强制下次刷新"""
    _cache.clear()
    return JSONResponse({"ok": True, "message": "Cache cleared"})


@app.get("/api/health")
async def health():
    sources = {
        "weibo": bool(cache_get("weibo")),
        "bilibili": bool(cache_get("bilibili")),
        "douyin": bool(cache_get("douyin")),
        "v2ex": bool(cache_get("v2ex")),
        "xhs": bool(cache_get("xhs")),
        "agent_reach": HAS_AGENT_REACH,
    }
    return JSONResponse({"ok": True, "cache": sources, "ts": int(time.time())})


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError:
        print("uvicorn not found. Run: python -m pip install uvicorn", file=sys.stderr)
        sys.exit(1)

    print("ReachALL API starting on http://localhost:8765")
    print("Endpoints:")
    print("  GET  /api/trends           — all platforms")
    print("  GET  /api/trends/<name>    — single platform")
    print("  POST /api/generate         — generate post with MiniMax")
    print("  POST /api/cache/clear      — flush cache")
    print("  GET  /api/health           — status")
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")
