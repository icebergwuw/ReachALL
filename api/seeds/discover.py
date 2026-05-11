"""
POST /api/seeds/discover
Body: {product, market, competitors}
"""
import json, sys, os, time
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
from _lib import discover_seed_keywords, DEEPSEEK_MODEL


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

        product = (payload.get("product") or "EasyClaw").strip()
        market = (payload.get("market") or "AI Agent / Web Automation").strip()
        competitors = payload.get("competitors") or ["n8n", "Zapier", "Dify", "Browser Use", "OpenAI Operator", "Manus", "Skyvern"]
        if isinstance(competitors, str):
            competitors = [x.strip() for x in competitors.split(",") if x.strip()]

        try:
            seeds = discover_seed_keywords(product, market, competitors)
            self._json({
                "ok": True,
                "product": product,
                "market": market,
                "competitors": competitors,
                "model": DEEPSEEK_MODEL,
                "updated_at": int(time.time()),
                "seeds": seeds,
            })
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass
