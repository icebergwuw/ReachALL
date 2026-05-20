# -*- coding: utf-8 -*-
"""
共享工具函数 — 热榜抓取 + DeepSeek 调用
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
TIMEOUT = 6
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# ── LLM provider ──────────────────────────────────────────────────────────────
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


# ── Prompts ───────────────────────────────────────────────────────────────────
# 仅保留 5 个目标发布平台：小红书 / 微信公众号 / X / 长视频脚本 / 短视频脚本
PLATFORM_GUIDES = {
    "xhs": {
        "name": "小红书",
        "max_len": 500,
        "style": "种草感强，真实分享语气，多用 emoji，标题党但不浮夸，末尾 6 个话题标签 #标签#",
    },
    "wechat": {
        "name": "微信公众号",
        "max_len": 2000,
        "style": "专业深度，有故事有干货，适合长文",
    },
    "x": {
        "name": "X (Twitter)",
        "max_len": 280,
        "style": (
            "用英文输出。开头一句话钩子，观点直接，1-2 个高相关 hashtag。"
            "面向海外开发者 / AI 社区（n8n / Zapier / browser-use 等用户），"
            "突出问题—洞察—可验证价值，避免硬广。"
        ),
    },
    "longvideo": {
        "name": "长视频脚本",
        "max_len": 1200,
        "style": (
            "面向 5 分钟 B 站 / YouTube 视频。结构：\n"
            "① 开场钩子（10-15 秒，提出读者真实痛点或反直觉观点）\n"
            "② 背景与冲突（30-45 秒，结合当前热点说明 why now）\n"
            "③ 主体 3 个段落（每段 60-90 秒：观点 + 故事/案例 + EasyClaw 自然出现）\n"
            "④ 金句一句\n"
            "⑤ CTA（订阅 / 评论 / 下载）\n"
            "用【画面】【口播】【字幕】三栏式标注每一段，方便直接拍摄。"
        ),
    },
    "shortvideo": {
        "name": "短视频脚本",
        "max_len": 400,
        "style": (
            "面向 15-30 秒抖音 / 小红书 / TikTok 短视频。结构：\n"
            "① 0-3 秒钩子：一句直击痛点或反差感的话\n"
            "② 4-20 秒主体：1 个具体场景 + EasyClaw 解法（口语化，节奏快）\n"
            "③ 21-30 秒收束：金句 + CTA（评论 / 关注 / 主页领取）\n"
            "用【画面】【口播】两栏标注每一段。文字总量控制在 400 字内。"
        ),
    },
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
    """Fetch Google Trends — daily/weekly hot searches for US, CN, JP, GLOBAL."""
    # (geo, hl, label)
    regions = [
        ("US", "en-US", "US"),
        ("JP", "ja-JP", "JP"),
        ("",   "en-US", "Global"),
    ]
    result = []
    for geo, hl, label in regions:
        geo_param = f"&geo={geo}" if geo else ""
        for hours, period in [(24, "Daily"), (168, "Weekly")]:
            url = f"https://trends.google.com/trending/rss?hl={hl}{geo_param}&hours={hours}"
            try:
                xml = _fetch_text(url, headers={"User-Agent": _UA_DESKTOP})
                root = ET.fromstring(xml)
                for i, item in enumerate(root.findall("./channel/item")[:15]):
                    title = _xml_text(item, "title")
                    traffic = _xml_text(item, "{https://trends.google.com/trending/rss}approx_traffic")
                    result.append({
                        "id": f"gt_{geo}_{hours}_{i}",
                        "platform": "google_trends",
                        "rank": i + 1,
                        "title": title,
                        "heat": 20 - i,
                        "heatLabel": traffic or "Trending",
                        "category": f"{label} {period} Hot",
                        "url": _xml_text(item, "link") or f"https://www.google.com/search?q={quote(title)}",
                    })
            except Exception as e:
                print(f"[google_trends {label} {period}] {e}")
    return result


def fetch_twitter() -> list[dict]:
    """Fetch AI/Tech trending tweets using Twitter API v2."""
    try:
        token = os.environ.get("TWITTER_BEARER_TOKEN", "")
        if not token:
            return []
        url = "https://api.twitter.com/2/tweets/search/recent?" + urlencode({
            "query": "(AI OR OpenAI OR Claude OR automation OR agent OR workflow OR LLM OR browser OR n8n OR Zapier OR EasyClaw) -is:retweet lang:en",
            "max_results": 20,
            "tweet.fields": "public_metrics,created_at,author_id",
            "sort_order": "relevancy",
        })
        data = _fetch_json(url, headers={
            "User-Agent": "ReachALL/1.0",
            "Authorization": f"Bearer {token}",
        })
        result = []
        for i, tweet in enumerate(data.get("data", [])[:20]):
            metrics = tweet.get("public_metrics", {})
            likes = metrics.get("like_count", 0)
            retweets = metrics.get("retweet_count", 0)
            result.append({
                "id": f"tw_{tweet.get('id', i)}", "platform": "twitter", "rank": i + 1,
                "title": tweet.get("text", "")[:280],
                "heat": likes + retweets * 5,
                "heatLabel": f"{likes}❤️ {retweets}🔁",
                "category": "Tweet",
                "url": f"https://twitter.com/i/web/status/{tweet.get('id', '')}",
            })
        return result
    except Exception as e:
        print(f"[twitter] {e}")
        return []



# ── Deep Search Functions ─────────────────────────────────────────────────────
def search_github_issues(seed: str) -> list[dict]:
    """Search GitHub Issues for real user complaints, feature requests, bugs."""
    try:
        query = f'"{seed}" is:issue state:open comments:>1'
        url = "https://api.github.com/search/issues?" + urlencode({
            "q": query,
            "sort": "reactions",
            "order": "desc",
            "per_page": 10,
        })
        data = _fetch_json(url, headers={
            "User-Agent": "ReachALL/1.0",
            "Accept": "application/vnd.github+json",
        })
        result = []
        for i, item in enumerate(data.get("items", [])[:10]):
            repo = item.get("repository_url", "").replace("https://api.github.com/repos/", "")
            result.append({
                "id": f"ghi_{item.get('id', i)}", "platform": "github_issue", "rank": i + 1,
                "title": item.get("title", ""),
                "body": (item.get("body") or "")[:800],
                "state": item.get("state", "open"),
                "comments": item.get("comments", 0),
                "url": item.get("html_url", ""),
                "repo": repo,
                "heat": item.get("comments", 0) * 100,
                "heatLabel": f"{item.get('comments', 0)} comments",
            })
        return result
    except Exception as e:
        print(f"[github_issues] {e}")
        return []


def search_reddit_posts_v2(seed: str) -> list[dict]:
    """Search Reddit posts + comments for real user voices."""
    try:
        query = f'"{seed}"'
        data = _fetch_json(
            "https://api.pullpush.io/reddit/search/submission/?" + urlencode({
                "q": query,
                "sort_type": "score",
                "sort": "desc",
                "size": 10,
            }),
            headers={"User-Agent": "ReachALL/1.0 trend reader"},
        )
        result = []
        for i, item in enumerate(data.get("data", [])[:10]):
            score = item.get("score", 0)
            permalink = item.get("permalink", "")
            post_id = item.get("id", f"rdp_{i}")
            comments = []
            try:
                comments_data = _fetch_json(
                    f"https://api.pullpush.io/reddit/search/comment/?link_id={post_id}&sort_type=score&sort=desc&size=5",
                    headers={"User-Agent": "ReachALL/1.0 trend reader"},
                )
                for c in comments_data.get("data", [])[:5]:
                    comments.append(c.get("body", ""))
            except Exception:
                pass
            result.append({
                "id": f"rdp2_{post_id}", "platform": "reddit_post_v2", "rank": i + 1,
                "title": item.get("title", ""),
                "selftext": (item.get("selftext") or "")[:600],
                "heat": score,
                "heatLabel": f"{score} 分",
                "category": f"r/{item.get('subreddit', '')}",
                "url": "https://www.reddit.com" + permalink if permalink.startswith("/") else item.get("url", ""),
                "author": item.get("author", ""),
                "comments": comments,
            })
        return result
    except Exception as e:
        print(f"[reddit_search_v2] {e}")
        return []


def search_reddit_posts(seed: str) -> list[dict]:
    """Search Reddit for real user voices and complaints bearing seed keyword."""
    try:
        query = f'"{seed}"'
        data = _fetch_json(
            "https://api.pullpush.io/reddit/search/submission/?" + urlencode({
                "q": query,
                "sort_type": "score",
                "sort": "desc",
                "size": 10,
            }),
            headers={"User-Agent": "ReachALL/1.0 trend reader"},
        )
        result = []
        for i, item in enumerate(data.get("data", [])[:10]):
            score = item.get("score", 0)
            permalink = item.get("permalink", "")
            result.append({
                "id": f"rdp_{item.get('id', i)}", "platform": "reddit_post", "rank": i + 1,
                "title": item.get("title", ""),
                "selftext": (item.get("selftext") or "")[:600],
                "heat": score,
                "heatLabel": f"{score} 分",
                "category": f"r/{item.get('subreddit', '')}",
                "url": "https://www.reddit.com" + permalink if permalink.startswith("/") else item.get("url", ""),
                "author": item.get("author", ""),
            })
        return result
    except Exception as e:
        print(f"[reddit_search] {e}")
        return []


def search_youtube_competitor(competitor: str) -> list[dict]:
    """Search YouTube reviews/tutorials about a competitor and extract pain points from top comments.

    Follows PDF Stage 1: find high-comment review/tutorial/problem videos
    Stage 2: categorize comment pain points (tech barrier / execution failure / pricing / missing features)
    """
    try:
        if not YOUTUBE_API_KEY:
            return []
        url = "https://www.googleapis.com/youtube/v3/search?" + urlencode({
            "part": "snippet",
            "type": "video",
            "order": "relevance",
            "maxResults": 5,
            "q": f"{competitor} review OR alternative OR problem OR why",
            "key": YOUTUBE_API_KEY,
        })
        data = _fetch_json(url, headers={"User-Agent": "ReachALL/1.0"})
        result = []
        for i, item in enumerate(data.get("items", [])[:5]):
            video_id = item.get("id", {}).get("videoId", "")
            snippet = item.get("snippet", {})
            comments = []
            if video_id:
                try:
                    comments_url = "https://www.googleapis.com/youtube/v3/commentThreads?" + urlencode({
                        "part": "snippet",
                        "videoId": video_id,
                        "maxResults": 10,
                        "order": "relevance",
                        "key": YOUTUBE_API_KEY,
                    })
                    comments_data = _fetch_json(comments_url, headers={"User-Agent": "ReachALL/1.0"})
                    for c in (comments_data.get("items") or [])[:10]:
                        top = c.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                        comments.append(top.get("textDisplay", ""))
                except Exception:
                    pass
            # categorize pain points
            pain_categories = {
                "tech_barrier": [],
                "execution_failure": [],
                "pricing": [],
                "missing_features": [],
            }
            all_text = (snippet.get("description", "") + " " + " ".join(comments)).lower()
            if any(w in all_text for w in ["hard to set up","confusing","complex","difficult","steep learning"]):
                pain_categories["tech_barrier"].append("setup/deployment complexity")
            if any(w in all_text for w in ["fail","crash","error","bug","broken","doesn't work","timeout"]):
                pain_categories["execution_failure"].append("execution instability")
            if any(w in all_text for w in ["expensive","price","cost","billing","overpriced"]):
                pain_categories["pricing"].append("pricing complaints")
            if any(w in all_text for w in ["wish it had","missing","no support for","can't","doesn't support"]):
                pain_categories["missing_features"].append("feature gaps")
            result.append({
                "id": f"ytc_{video_id or i}", "platform": "youtube_competitor", "rank": i + 1,
                "title": snippet.get("title", ""),
                "description": (snippet.get("description", ""))[:400],
                "author": snippet.get("channelTitle", ""),
                "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "https://www.youtube.com",
                "comments": comments,
                "pain_categories": pain_categories,
            })
        return result
    except Exception as e:
        print(f"[youtube_competitor] {e}")
        return []


def search_youtube_videos(seed: str) -> list[dict]:
    """Search YouTube videos + fetch top comments for each result."""
    try:
        if not YOUTUBE_API_KEY:
            return []
        url = "https://www.googleapis.com/youtube/v3/search?" + urlencode({
            "part": "snippet",
            "type": "video",
            "order": "relevance",
            "maxResults": 5,
            "q": seed,
            "key": YOUTUBE_API_KEY,
        })
        data = _fetch_json(url, headers={"User-Agent": "ReachALL/1.0"})
        result = []
        for i, item in enumerate(data.get("items", [])[:5]):
            video_id = item.get("id", {}).get("videoId", "")
            snippet = item.get("snippet", {})
            comments = []
            if video_id:
                try:
                    comments_url = "https://www.googleapis.com/youtube/v3/commentThreads?" + urlencode({
                        "part": "snippet",
                        "videoId": video_id,
                        "maxResults": 5,
                        "order": "relevance",
                        "key": YOUTUBE_API_KEY,
                    })
                    comments_data = _fetch_json(comments_url, headers={"User-Agent": "ReachALL/1.0"})
                    for c in (comments_data.get("items") or [])[:5]:
                        top = c.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                        comments.append(top.get("textDisplay", ""))
                except Exception:
                    pass
            result.append({
                "id": f"ytv_{video_id or i}", "platform": "youtube_video", "rank": i + 1,
                "title": snippet.get("title", ""),
                "description": (snippet.get("description", ""))[:400],
                "author": snippet.get("channelTitle", ""),
                "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "https://www.youtube.com",
                "comments": comments,
            })
        return result
    except Exception as e:
        print(f"[youtube_search] {e}")
        return []


def search_twitter(seed: str) -> list[dict]:
    """Search Twitter for real user opinions and complaints bearing seed keyword."""
    try:
        token = os.environ.get("TWITTER_BEARER_TOKEN", "")
        if not token:
            return []
        url = "https://api.twitter.com/2/tweets/search/recent?" + urlencode({
            "query": f'"{seed}" lang:en -is:retweet',
            "max_results": 10,
            "tweet.fields": "public_metrics,created_at,author_id",
            "sort_order": "relevancy",
        })
        data = _fetch_json(url, headers={
            "User-Agent": "ReachALL/1.0",
            "Authorization": f"Bearer {token}",
        })
        result = []
        for i, tweet in enumerate(data.get("data", [])[:10]):
            metrics = tweet.get("public_metrics", {})
            likes = metrics.get("like_count", 0)
            retweets = metrics.get("retweet_count", 0)
            result.append({
                "id": f"tws_{tweet.get('id', i)}", "platform": "twitter_search", "rank": i + 1,
                "title": tweet.get("text", "")[:280],
                "body": tweet.get("text", "")[:400],
                "heat": likes + retweets * 5,
                "heatLabel": f"{likes}❤️ {retweets}🔁",
                "url": f"https://twitter.com/i/web/status/{tweet.get('id', '')}",
            })
        return result
    except Exception as e:
        print(f"[twitter_search] {e}")
        return []


# ── SEO / Demand Research Agent ───────────────────────────────────────────────
def collect_research_signals(seed: str) -> dict:
    """Collect cross-channel signals — trending feeds + deep search for seed."""
    seed_lower = (seed or "").lower()
    sources = {
        "github": fetch_github,
        "reddit": fetch_reddit,
        "youtube": fetch_youtube,
        "producthunt": fetch_producthunt,
        "google_trends": fetch_google_trends,
        "hackernews": fetch_hackernews,
        "twitter": fetch_twitter,
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
            repo = item.get("repo", "")
            lines.append(f"- {title} | {heat} | {author} | {'repo:'+repo if repo else ''} | {url}")
            # Deep data
            body = item.get("body", "") or item.get("selftext", "") or ""
            if body:
                lines.append(f"  内容摘要: {body[:300]}")
            comments = item.get("comments", "")
            if isinstance(comments, list):
                for ci, c in enumerate(comments[:5]):
                    lines.append(f"  评论{ci+1}: {c[:250]}")
            pain = item.get("pain_categories")
            if pain and isinstance(pain, dict):
                pains = {k: v for k, v in pain.items() if v}
                if pains:
                    lines.append(f"  痛点归类: {json.dumps(pains, ensure_ascii=False)}")
    return "\n".join(lines)


def build_research_report(seed: str, product: str, goal: str, signals: dict) -> str:
    system = """你是全渠道市场情报与SEO需求挖掘专家。你擅长从搜索趋势、社区讨论、开源项目Issue和YouTube视频评论里提炼用户痛点、竞品缺口和高意图关键词。

当输入信号包含 reddit_post_v2 的 comments 字段、youtube_competitor 的 pain_categories 字段、github_repo_issue 的 body 字段时，你必须在报告中引用它们作为"用户原声"。

严格遵循以下原则：
1. 审查每个信号源的 title/body/selftext/comments/pain_categories。
2. 优先从 YouTube 视频评论和 Reddit 帖子评论中提取原始用户语言，作为"用户原声片段"。
3. 从 GitHub repo issues 的 body 中提取功能缺失、痛点、技术障碍。
4. 按指定结构输出，每个论据引用具体的来源和 URL。
5. 输出必须具体、可执行，避免空泛营销话术。"""
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
提取 5-8 个真实用户痛点。优先使用 GitHub Issues 的 body、Reddit 帖子的 selftext、YouTube 视频评论的原话。

## 4. 竞品防线缺口
总结竞品或现有方案在哪些地方弱：价格、部署、稳定性、技术门槛、隐私、工作流复杂度。

## 5. 高意图关键词
输出 12 个关键词，分为：功能词、对比词、场景词。每个词给出搜索意图和内容角度。

## 6. 内容切入点
给出 8 个可直接用于博客/推文/视频的标题。

## 7. 下一步验证动作
给出 5 个低成本验证动作，例如写文章、发帖、做对比页、搜索更多评论等。
"""
    return call_deepseek(prompt, system=system, max_tokens=2500)  # keep within 60s


def _parse_json_object(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


def discover_seed_keywords(product: str = "EasyClaw", market: str = "AI Agent / Web Automation", competitors: list[str] = None) -> list[dict]:
    competitors = competitors or ["n8n", "Zapier", "Dify", "Browser Use", "OpenAI Operator", "Manus", "Skyvern", "Playwright", "Puppeteer"]
    signals = collect_research_signals(market)
    system = """你是SEO种子词发现Agent。你的任务不是写报告，而是从产品定位、竞品、社区趋势和用户痛点中发现可用于SEO/内容/增长实验的高价值种子关键词。只输出JSON，不要输出解释。"""
    prompt = f"""请为以下产品自动发现SEO/需求挖掘种子词。

目标产品：{product}
目标市场：{market}
竞品/参考对象：{', '.join(competitors)}

多渠道信号：
{_signal_lines(signals)}

请输出严格JSON，格式如下：
{{
  "seeds": [
    {{
      "keyword": "n8n alternative",
      "type": "competitor|pain|scenario|trend|capability",
      "score": 94,
      "sources": ["reddit", "github"],
      "reason": "为什么这是高价值种子词",
      "next_action": "建议下一步动作"
    }}
  ]
}}

要求：
- 输出20个种子词
- keyword必须是用户可能真实搜索的英文SEO短语
- type只能是 competitor/pain/scenario/trend/capability 之一
- score是0-100的整数
- 优先选择和本地AI Agent、浏览器自动化、工作流自动化、竞品替代、隐私/价格/部署痛点相关的词
- 不要输出泛泛的AI新闻词
"""
    data = _parse_json_object(call_deepseek(prompt, system=system, max_tokens=4000))
    seeds = data.get("seeds", []) if isinstance(data, dict) else []
    normalized = []
    for item in seeds[:30]:
        if not isinstance(item, dict):
            continue
        keyword = str(item.get("keyword", "")).strip()
        if not keyword:
            continue
        normalized.append({
            "keyword": keyword,
            "type": item.get("type", "trend"),
            "score": int(item.get("score", 0) or 0),
            "sources": item.get("sources", []),
            "reason": item.get("reason", ""),
            "next_action": item.get("next_action", ""),
        })
    return sorted(normalized, key=lambda x: x.get("score", 0), reverse=True)
def search_github_repo_issues() -> list[dict]:
    """Scan issues from 10 high-value competitor/adjacent repos per the SEO Agent spec."""
    repos = [
        "browser-use/browser-use",
        "Skyvern-AI/skyvern",
        "n8n-io/n8n",
        "langgenius/dify",
        "microsoft/playwright",
        "unclecode/crawl4ai",
        "browserbase/stagehand",
        "scrapy/scrapy",
    ]

    all_issues = []
    for repo in repos:
        try:
            query = f"repo:{repo} is:issue state:open comments:>2"
            url = "https://api.github.com/search/issues?" + urlencode({
                "q": query,
                "sort": "comments",
                "order": "desc",
                "per_page": 3,
            })
            data = _fetch_json(url, headers={
                "User-Agent": "ReachALL/1.0",
                "Accept": "application/vnd.github+json",
            })
            for i, item in enumerate(data.get("items", [])[:3]):
                all_issues.append({
                    "id": f"ghri_{item.get('id', i)}",
                    "platform": "github_repo_issue",
                    "rank": i + 1,
                    "title": item.get("title", ""),
                    "body": (item.get("body") or "")[:800],
                    "state": item.get("state", "open"),
                    "comments": item.get("comments", 0),
                    "url": item.get("html_url", ""),
                    "repo": repo,
                    "heat": item.get("comments", 0) * 100,
                    "heatLabel": f"{item.get('comments', 0)} comments",
                })
        except Exception as e:
            print(f"[github_repo_issues {repo}] {e}")
            continue
    return all_issues
