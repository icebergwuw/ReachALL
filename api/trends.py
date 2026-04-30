"""
GET /api/trends?platform=all|weibo|bilibili|douyin|v2ex
"""
import json, sys, os, time
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from _lib import fetch_weibo, fetch_bilibili, fetch_douyin, fetch_v2ex


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        platform = params.get("platform", ["all"])[0]

        fetchers = {
            "weibo":    fetch_weibo,
            "bilibili": fetch_bilibili,
            "douyin":   fetch_douyin,
            "v2ex":     fetch_v2ex,
        }

        items, sources = [], {}

        if platform == "all":
            for name, fn in fetchers.items():
                try:
                    res = fn()
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
        })

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass
