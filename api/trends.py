"""
GET /api/trends?platform=all|weibo|bilibili|douyin|v2ex|github|reddit|hackernews|producthunt|youtube|google_trends|twitter
"""
import json, sys, os, time
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from _lib import (
    fetch_weibo, fetch_bilibili, fetch_douyin, fetch_v2ex,
    fetch_github, fetch_reddit, fetch_hackernews, fetch_producthunt,
    fetch_youtube, fetch_google_trends, fetch_twitter,
)

FETCHERS = {
    "weibo":         fetch_weibo,
    "bilibili":      fetch_bilibili,
    "douyin":        fetch_douyin,
    "v2ex":          fetch_v2ex,
    "github":        fetch_github,
    "reddit":        fetch_reddit,
    "hackernews":    fetch_hackernews,
    "producthunt":   fetch_producthunt,
    "youtube":       fetch_youtube,
    "google_trends": fetch_google_trends,
    "twitter":       fetch_twitter,
}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        platform = params.get("platform", ["all"])[0]

        fetchers = FETCHERS

        items, sources = [], {}

        if platform == "all":
            with ThreadPoolExecutor(max_workers=len(fetchers)) as pool:
                future_to_name = {pool.submit(fn): name for name, fn in fetchers.items()}
                for future in as_completed(future_to_name):
                    name = future_to_name[future]
                    try:
                        res = future.result()
                        sources[name] = len(res)
                        items.extend(res)
                    except Exception as e:
                        print(f"[trends] {name}: {e}")
        elif platform in fetchers:
            try:
                items = fetchers[platform]()
                sources[platform] = len(items)
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, 500)
                return
        else:
            self._json({"ok": False, "error": f"Unknown platform: {platform}"}, 404)
            return

        self._json({
            "ok": True,
            "total": len(items),
            "sources": sources,
            "updated_at": int(time.time()),
            "items": items,
        }, cache=True)

    def _json(self, data, status=200, cache=False):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        if cache:
            # Vercel CDN 缓存10分钟，stale-while-revalidate 后台更新
            self.send_header("Cache-Control", "s-maxage=600, stale-while-revalidate=60")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass
