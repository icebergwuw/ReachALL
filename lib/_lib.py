# -*- coding: utf-8 -*-
"""
共享工具函数 — 热榜抓取 + MiniMax 调用
供 Vercel serverless functions 引用
"""

import json
import os
import time
import datetime as _dt
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
from urllib.parse import quote, urlencode
from typing import Any

# ── Config ────────────────────────────────────────────────────────────────────
_UA_DESKTOP = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_UA_MOBILE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
)
TIMEOUT = 10
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# ── LLM providers ─────────────────────────────────────────────────────────────
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_MODEL   = "MiniMax-M2.5-highspeed"
MINIMAX_URL     = "https://api.minimax.chat/v1/text/chatcompletion_v2"

DEEPSEEK_API_KEY  = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL    = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_URL      = DEEPSEEK_BASE_URL.rstrip("/") + "/chat/completions"


def call_deepseek(prompt: str, system: str = None, max_tokens: int = 4096) -> str:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }).encode()

    req = urllib.request.Request(DEEPSEEK_URL, data=payload, headers={
        "Authorization": "Bearer " + DEEPSEEK_API_KEY,
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"DeepSeek HTTP {e.code}: {detail}") from e

    error = data.get("error")
    if error:
        raise RuntimeError(f"DeepSeek error: {error}")

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("DeepSeek returned no choices")
    return choices[0].get("message", {}).get("content", "").strip()


def call_minimax(prompt: str, system: str = None, max_tokens: int = 4096) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model": MINIMAX_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
    }).encode()

    req = urllib.request.Request(MINIMAX_URL, data=payload, headers={
        "Authorization": "Bearer " + MINIMAX_API_KEY,
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode())

    base = data.get("base_resp", {})
    if base.get("status_code", 0) != 0:
        raise RuntimeError(f"MiniMax error {base.get('status_code')}: {base.get('status_msg')}")

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("MiniMax returned no choices")
    return choices[0].get("message", {}).get("content", "").strip()


# ── Prompts ───────────────────────────────────────────────────────────────────
PLATFORM_GUIDES = {
    "weibo":    {"name": "微博",   "max_len": 140, "style": "简洁有力，结尾加2-3个话题标签 #话题#"},
    "douyin":   {"name": "抖音",   "max_len": 150, "style": "开头直接抓眼球，口语化，引发互动，结尾5个话题标签"},
    "xhs":      {"name": "小红书", "max_len": 500, "style": "种草感强，真实分享语气，多用emoji，末尾6个话题标签"},
    "bilibili": {"name": "B站",    "max_len": 200, "style": "二次元/科技向，有趣有深度，结尾@相关UP主方向"},
    "v2ex":     {"name": "V2EX",  "max_len": 300, "style": "技术社区，干货为主，理性客观，程序员视角"},
    "wechat":   {"name": "微信公众号", "max_len": 2000, "style": "专业深度，有故事有干货，适合长文"},
    "github":   {"name": "GitHub", "max_len": 280, "style": "面向开发者，突出项目价值、技术亮点和可尝试场景"},
    "reddit":   {"name": "Reddit", "max_len": 300, "style": "英文社区讨论感，观点直接，适合引发评论互动"},
    "hackernews": {"name": "Hacker News", "max_len": 300, "style": "技术创业视角，理性克制，强调问题、洞察和可验证价值"},
    "producthunt": {"name": "Product Hunt", "max_len": 260, "style": "新产品发布口吻，强调一句话价值、使用场景和行动号召"},
    "youtube":  {"name": "YouTube", "max_len": 300, "style": "视频标题/简介风格，开头抓注意力，适合频道观众点击"},
    "google_trends": {"name": "Google Trends", "max_len": 280, "style": "全球趋势解读，快速说明为什么火、和AI效率工具的关联"},
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

WECHAT_SYSTEM_PROMPT = """你是 EasyClaw 品牌微信公众号的资深内容运营，专门创作高质量推文。
EasyClaw 是猎豹移动出品的桌面 AI Agent 工具：无代码零配置、本地沙盒、远程手机控制电脑、自动化重复工作。
品牌色：橙色 #FF5722。"""


# ── Helpers ───────────────────────────────────────────────────────────────────
def _fetch_json(url: str, headers: dict = None) -> Any:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": _UA_DESKTOP})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _fetch_text(url: str, headers: dict = None) -> str:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": _UA_DESKTOP})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", errors="replace")


def _xml_text(node, tag: str) -> str:
    found = node.find(tag)
    return (found.text or "").strip() if found is not None else ""


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
            result.append({
                "id": f"wb_{i}", "platform": "weibo", "rank": i + 1,
                "title": title, "heat": heat, "heatLabel": _format_heat(heat),
                "category": item.get("category", ""),
                "url": f"https://s.weibo.com/weibo?q={quote(title)}",
            })
        return result
    except Exception as e:
        print(f"[weibo] {e}")
        return []


def fetch_bilibili() -> list[dict]:
    try:
        data = _fetch_json(
            "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all",
            headers={"User-Agent": _UA_DESKTOP, "Referer": "https://www.bilibili.com"},
        )
        items = data.get("data", {}).get("list", [])
        result = []
        for i, item in enumerate(items[:20]):
            view = item.get("stat", {}).get("view", 0)
            result.append({
                "id": f"bili_{i}", "platform": "bilibili", "rank": i + 1,
                "title": item.get("title", ""), "heat": view,
                "heatLabel": _format_heat(view),
                "category": item.get("tname", ""),
                "url": f"https://www.bilibili.com/video/{item.get('bvid','')}",
                "author": item.get("owner", {}).get("name", ""),
            })
        return result
    except Exception as e:
        print(f"[bilibili] {e}")
        return []


def fetch_douyin() -> list[dict]:
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
                "id": f"dy_{i}", "platform": "douyin", "rank": i + 1,
                "title": item.get("word", ""), "heat": heat,
                "heatLabel": _format_heat(heat),
                "category": item.get("sentence_tag", ""),
                "url": f"https://www.douyin.com/search/{quote(item.get('word',''))}",
            })
        return result
    except Exception as e:
        print(f"[douyin] {e}")
        return []


def fetch_v2ex() -> list[dict]:
    try:
        data = _fetch_json(
            "https://www.v2ex.com/api/v2/topics/hot.json",
            headers={"User-Agent": _UA_DESKTOP},
        )
        items = data.get("result", [])
        result = []
        for i, item in enumerate(items[:20]):
            replies = item.get("replies", 0)
            result.append({
                "id": f"v2ex_{item.get('id',i)}", "platform": "v2ex", "rank": i + 1,
                "title": item.get("title", ""),
                "heat": replies * 1000, "heatLabel": f"{replies} 回复",
                "category": item.get("node", {}).get("title", ""),
                "url": item.get("url", ""),
            })
        return result
    except Exception as e:
        print(f"[v2ex] {e}")
        return []


def fetch_github() -> list[dict]:
    try:
        since = (_dt.date.today() - _dt.timedelta(days=14)).isoformat()
        query = f"stars:>500 pushed:>{since}"
        url = "https://api.github.com/search/repositories?" + urlencode({
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 20,
        })
        data = _fetch_json(url, headers={
            "User-Agent": "ReachALL/1.0",
            "Accept": "application/vnd.github+json",
        })
        result = []
        for i, item in enumerate(data.get("items", [])[:20]):
            stars = item.get("stargazers_count", 0)
            result.append({
                "id": f"gh_{item.get('full_name', i)}", "platform": "github", "rank": i + 1,
                "title": item.get("full_name", ""), "heat": stars,
                "heatLabel": f"{_format_heat(stars)} stars",
                "category": item.get("language") or "Repository",
                "url": item.get("html_url", ""),
                "author": item.get("owner", {}).get("login", ""),
                "summary": item.get("description") or "",
            })
        return result
    except Exception as e:
        print(f"[github] {e}")
        return []


def fetch_reddit() -> list[dict]:
    def normalize_official(children: list) -> list[dict]:
        result = []
        for i, child in enumerate(children[:20]):
            item = child.get("data", {})
            score = item.get("score", 0)
            permalink = item.get("permalink", "")
            result.append({
                "id": f"rd_{item.get('id', i)}", "platform": "reddit", "rank": i + 1,
                "title": item.get("title", ""), "heat": score,
                "heatLabel": f"{score} 分",
                "category": f"r/{item.get('subreddit', '')}",
                "url": "https://www.reddit.com" + permalink if permalink.startswith("/") else permalink,
                "author": item.get("author", ""),
            })
        return result

    def normalize_pullpush(posts: list) -> list[dict]:
        result = []
        for i, item in enumerate(posts[:20]):
            score = item.get("score", 0)
            permalink = item.get("permalink", "")
            result.append({
                "id": f"rd_{item.get('id', i)}", "platform": "reddit", "rank": i + 1,
                "title": item.get("title", ""), "heat": score,
                "heatLabel": f"{score} 分",
                "category": f"r/{item.get('subreddit', '')}",
                "url": "https://www.reddit.com" + permalink if permalink.startswith("/") else item.get("url", ""),
                "author": item.get("author", ""),
            })
        return result

    try:
        data = _fetch_json(
            "https://www.reddit.com/r/technology/hot.json?limit=20&raw_json=1",
            headers={"User-Agent": "ReachALL/1.0 trend reader"},
        )
        result = normalize_official(data.get("data", {}).get("children", []))
        if result:
            return result
    except Exception as e:
        print(f"[reddit official] {e}")

    try:
        data = _fetch_json(
            "https://api.pullpush.io/reddit/search/submission/?subreddit=technology&sort_type=score&sort=desc&size=20",
            headers={"User-Agent": "ReachALL/1.0 trend reader"},
        )
        return normalize_pullpush(data.get("data", []))
    except Exception as e:
        print(f"[reddit pullpush] {e}")
        return []


def fetch_hackernews() -> list[dict]:
    try:
        data = _fetch_json(
            "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=20",
            headers={"User-Agent": "ReachALL/1.0"},
        )
        result = []
        for i, item in enumerate(data.get("hits", [])[:20]):
            points = item.get("points") or 0
            comments = item.get("num_comments") or 0
            story_id = item.get("objectID", i)
            result.append({
                "id": f"hn_{story_id}", "platform": "hackernews", "rank": i + 1,
                "title": item.get("title") or item.get("story_title", ""), "heat": points,
                "heatLabel": f"{points} 分 · {comments} 评论",
                "category": "Hacker News",
                "url": item.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
                "author": item.get("author", ""),
            })
        return result
    except Exception as e:
        print(f"[hackernews] {e}")
        return []


def fetch_producthunt() -> list[dict]:
    try:
        xml = _fetch_text("https://www.producthunt.com/feed", headers={"User-Agent": _UA_DESKTOP})
        root = ET.fromstring(xml)
        result = []
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")
        for i, item in enumerate(entries[:20]):
            title = _xml_text(item, "{http://www.w3.org/2005/Atom}title")
            link = item.find("{http://www.w3.org/2005/Atom}link")
            url = link.attrib.get("href", "") if link is not None else ""
            desc = _xml_text(item, "{http://www.w3.org/2005/Atom}content") or _xml_text(item, "{http://www.w3.org/2005/Atom}summary")
            result.append({
                "id": f"ph_{i}", "platform": "producthunt", "rank": i + 1,
                "title": title, "heat": 20 - i,
                "heatLabel": "Product Hunt",
                "category": "Product",
                "url": url,
                "summary": desc,
            })
        return result
    except Exception as e:
        print(f"[producthunt] {e}")
        return []


def fetch_youtube() -> list[dict]:
    try:
        if not YOUTUBE_API_KEY:
            return []
        query = "AI OR OpenAI OR Claude OR startup OR technology"
        url = "https://www.googleapis.com/youtube/v3/search?" + urlencode({
            "part": "snippet",
            "type": "video",
            "order": "relevance",
            "publishedAfter": (_dt.datetime.utcnow() - _dt.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "maxResults": 20,
            "q": query,
            "key": YOUTUBE_API_KEY,
        })
        data = _fetch_json(url, headers={"User-Agent": "ReachALL/1.0"})
        result = []
        for i, item in enumerate(data.get("items", [])[:20]):
            video_id = item.get("id", {}).get("videoId", "")
            snippet = item.get("snippet", {})
            result.append({
                "id": f"yt_{video_id or i}", "platform": "youtube", "rank": i + 1,
                "title": snippet.get("title", ""), "heat": 20 - i,
                "heatLabel": "YouTube",
                "category": "Video",
                "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "https://www.youtube.com",
                "author": snippet.get("channelTitle", ""),
                "publishedAt": snippet.get("publishedAt", ""),
            })
        return result
    except Exception as e:
        print(f"[youtube] {e}")
        return []


def fetch_google_trends() -> list[dict]:
    try:
        xml = _fetch_text(
            "https://trends.google.com/trending/rss?geo=US&hl=en-US",
            headers={"User-Agent": _UA_DESKTOP},
        )
        root = ET.fromstring(xml)
        result = []
        for i, item in enumerate(root.findall("./channel/item")[:20]):
            title = _xml_text(item, "title")
            traffic = _xml_text(item, "{https://trends.google.com/trending/rss}approx_traffic")
            result.append({
                "id": f"gt_{i}", "platform": "google_trends", "rank": i + 1,
                "title": title, "heat": 20 - i,
                "heatLabel": traffic or "Google Trends",
                "category": "Trending Search",
                "url": _xml_text(item, "link") or f"https://www.google.com/search?q={quote(title)}",
            })
        return result
    except Exception as e:
        print(f"[google_trends] {e}")
        return []


# ── SEO / Demand Research Agent ───────────────────────────────────────────────
def collect_research_signals(seed: str) -> dict:
    """Collect lightweight cross-channel signals for a seed keyword."""
    seed_lower = (seed or "").lower()
    sources = {
        "github": fetch_github,
        "reddit": fetch_reddit,
        "youtube": fetch_youtube,
        "producthunt": fetch_producthunt,
        "google_trends": fetch_google_trends,
        "hackernews": fetch_hackernews,
    }
    signals = {}
    for name, fn in sources.items():
        try:
            items = fn()
            matched = []
            for item in items:
                haystack = " ".join([
                    str(item.get("title", "")),
                    str(item.get("summary", "")),
                    str(item.get("category", "")),
                ]).lower()
                if not seed_lower or seed_lower in haystack:
                    matched.append(item)
            signals[name] = (matched or items)[:8]
        except Exception as e:
            print(f"[research:{name}] {e}")
            signals[name] = []
    return signals


def _signal_lines(signals: dict) -> str:
    lines = []
    for source, items in signals.items():
        lines.append(f"## {source}")
        if not items:
            lines.append("- 暂无有效信号")
            continue
        for item in items[:8]:
            title = item.get("title", "")
            heat = item.get("heatLabel", "")
            url = item.get("url", "")
            author = item.get("author", "")
            lines.append(f"- {title} | {heat} | {author} | {url}")
    return "\n".join(lines)


def build_research_report(seed: str, product: str, goal: str, signals: dict) -> str:
    system = """你是全渠道市场情报与SEO需求挖掘专家。你擅长从搜索趋势、社区讨论、开源项目、视频内容和产品评论里提炼用户痛点、竞品缺口和高意图关键词。输出必须具体、可执行，避免空泛营销话术。"""
    prompt = f"""请基于以下多渠道信号，为产品做一份中文市场机会分析报告。

种子词：{seed}
目标产品：{product}
战术目标：{goal}

多渠道信号：
{_signal_lines(signals)}

请严格按以下结构输出 Markdown：
# 市场机会分析报告

## 1. 一句话机会判断
用一句话判断这个方向是否值得做，以及为什么。

## 2. 趋势信号
按 Google Trends / GitHub / Reddit / YouTube / Product Hunt / Hacker News 分点总结，每点必须引用来源名称。

## 3. 用户痛点与原声
提取 5-8 个用户可能正在表达的痛点。尽量使用接近用户原话的表达。

## 4. 竞品防线缺口
总结竞品或现有方案在哪些地方弱：价格、部署、稳定性、技术门槛、隐私、工作流复杂度。

## 5. 高意图关键词
输出 12 个关键词，分为：功能词、对比词、场景词。每个词给出搜索意图和内容角度。

## 6. 内容切入点
给出 8 个可直接用于博客/推文/视频的标题。

## 7. 下一步验证动作
给出 5 个低成本验证动作，例如写文章、发帖、做对比页、搜索更多评论等。
"""
    return call_deepseek(prompt, system=system, max_tokens=5000)
