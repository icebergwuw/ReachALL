"""
POST /api/generate
Body: { topic_title, topic_heat, topic_platform, target_platform, tone, extra }
"""
import json, sys, os
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from _lib import call_deepseek, DEEPSEEK_MODEL, SYSTEM_PROMPT, PLATFORM_GUIDES, TONE_GUIDES


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")

        topic_title     = body.get("topic_title", "")
        topic_heat      = body.get("topic_heat", "")
        topic_platform  = body.get("topic_platform", "weibo")
        target_platform = body.get("target_platform", "xhs")
        tone            = body.get("tone", "营销种草")
        extra           = body.get("extra", "")

        plat_guide = PLATFORM_GUIDES.get(target_platform, PLATFORM_GUIDES["xhs"])
        tone_guide = TONE_GUIDES.get(tone, TONE_GUIDES["营销种草"])

        prompt = (
            f"当前热点话题：「{topic_title}」（热度：{topic_heat}）\n"
            f"来源平台：{topic_platform}\n"
            f"目标发布平台：{plat_guide['name']}\n"
            f"字数要求：不超过 {plat_guide['max_len']} 字\n"
            f"平台风格：{plat_guide['style']}\n"
            f"内容语气：{tone_guide}\n"
            + (f"额外要求：{extra}\n" if extra else "")
            + f"\n请为 EasyClaw 创作一条紧扣热点、自然植入的{plat_guide['name']}推广内容。"
        )

        try:
            text = call_deepseek(prompt, system=SYSTEM_PROMPT)
            self._json({"ok": True, "text": text, "model": DEEPSEEK_MODEL})
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, *args):
        pass
