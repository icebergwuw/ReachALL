# -*- coding: utf-8 -*-
"""
共享工具函数 — 热榜抓取 + MiniMax 调用
供 Vercel serverless functions 引用
"""

import json
import os
import time
import urllib.request
import urllib.error
from urllib.parse import quote
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

# ── MiniMax ───────────────────────────────────────────────────────────────────
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_MODEL   = "MiniMax-M2.5-highspeed"
MINIMAX_URL     = "https://api.minimax.chat/v1/text/chatcompletion_v2"

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
