"""
POST /api/search/deep
Body: {seed}
"""
import json, sys, os
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
from _lib import search_github_issues, search_reddit_posts, search_youtube_videos, search_twitter


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(body or "{}")
        except Exception:
            self._json({"ok": False, "error": "Invalid JSON body"}, 400)
            return

        seed = (payload.get("seed") or "").strip()
        if not seed:
            self._json({"ok": False, "error": "seed is required"}, 400)
            return

        signals = {}
        try:
            signals["github_issues"] = search_github_issues(seed)
        except Exception as e:
            signals["github_issues"] = []
            print(f"[deep] github_issues: {e}")

        try:
            signals["reddit_posts"] = search_reddit_posts(seed)
        except Exception as e:
            signals["reddit_posts"] = []
            print(f"[deep] reddit_posts: {e}")

        try:
            signals["youtube_videos"] = search_youtube_videos(seed)
        except Exception as e:
            signals["youtube_videos"] = []
            print(f"[deep] youtube_videos: {e}")

        try:
            signals["twitter_search"] = search_twitter(seed)
        except Exception as e:
            signals["twitter_search"] = []
            print(f"[deep] twitter_search: {e}")

        self._json({"ok": True, "seed": seed, "signals": signals})

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass
