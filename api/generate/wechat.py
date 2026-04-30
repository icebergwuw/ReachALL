"""
POST /api/generate/wechat
Body: { topic_title, topic_heat, topic_platform, article_type, tone, extra }
Returns: { ok, html, filename }
"""
import json, sys, os, re
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))
from _lib import call_minimax, WECHAT_SYSTEM_PROMPT


def _build_prompt(body: dict) -> str:
    topic_title    = body.get("topic_title", "")
    topic_heat     = body.get("topic_heat", "")
    topic_platform = body.get("topic_platform", "weibo")
    article_type   = body.get("article_type", "产品介绍")
    tone           = body.get("tone", "亲切简洁")
    extra          = body.get("extra", "")

    return (
        f"你的任务是生成一个完整的微信公众号推文 HTML 文件。\n\n"
        f"热点话题：「{topic_title}」（热度：{topic_heat}，来源：{topic_platform}）\n"
        f"文章类型：{article_type}\n"
        f"写作风格：{tone}\n"
        + (f"额外要求：{extra}\n" if extra else "")
        + "\n严格要求：\n"
        "1. 只输出 HTML 代码，第一个字符必须是 <，最后一个字符必须是 >\n"
        "2. 从 <!DOCTYPE html><html><head><meta charset=\"UTF-8\"></head><body> 开始\n"
        "3. 将 EasyClaw 的价值自然融入热点话题\n"
        "4. 全部使用 inline style，禁止 flex/grid，双列布局用 table\n"
        "5. 包含：题图标签橙色胶囊、小标题橙色竖条、正文段落、金句卡（橙底白字）、CTA结尾（橙底）、标签行\n"
        "6. 不要输出任何解释文字、markdown、代码块标记，直接输出纯 HTML\n\n"
        "现在直接输出 HTML："
    )


def _extract_html(text: str) -> str:
    for pattern in [
        r'(<!DOCTYPE[^>]*>[\s\S]*?</html>)',
        r'(<html[\s\S]*?</html>)',
        r'(<body[\s\S]*?</body>)',
    ]:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1)
    if not text.strip().startswith("<"):
        return (
            "<!DOCTYPE html><html><head><meta charset='UTF-8'></head><body>"
            + text + "</body></html>"
        )
    return text


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")

        prompt = _build_prompt(body)

        try:
            raw = call_minimax(prompt, system=WECHAT_SYSTEM_PROMPT, max_tokens=8192)
            html = _extract_html(raw)
            topic_title = body.get("topic_title", "article")
            safe = topic_title[:30].replace("/", "-").replace("\\", "-").replace(" ", "_")
            filename = f"{safe}-wechat.html"
            self._json({"ok": True, "html": html, "filename": filename})
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
