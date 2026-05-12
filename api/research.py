"""
POST /api/research
Body: {seed, product, goal}
"""
import json, sys, os, time
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        import traceback as _tb
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(body or "{}")
        except Exception:
            self._json({"ok": False, "error": "Invalid JSON body"}, 400)
            return

        seed = (payload.get("seed") or "").strip()
        product = (payload.get("product") or "EasyClaw").strip()
        goal = (payload.get("goal") or "寻找高意图SEO关键词和内容切入点").strip()
        if not seed:
            self._json({"ok": False, "error": "seed is required"}, 400)
            return

        try:
            from _lib import collect_research_signals, build_research_report, DEEPSEEK_MODEL

            # Step 1: collect only trending feeds (fast)
            signals = collect_research_signals(seed)

            # Step 2: generate report
            report = build_research_report(seed, product, goal, signals)

            self._json({
                "ok": True,
                "seed": seed,
                "product": product,
                "goal": goal,
                "model": DEEPSEEK_MODEL,
                "updated_at": int(time.time()),
                "signals": signals,
                "report": report,
            })
        except Exception as e:
            self._json({"ok": False, "error": str(e)[:500], "trace": _tb.format_exc()[-1000:]}, 500)

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass
