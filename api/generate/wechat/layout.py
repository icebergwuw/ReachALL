"""
POST /api/generate/wechat/layout  (Step 2 of 2)
Body: { article, topic_title }
Returns: { ok, html, filename, model, elapsed_ms }

把正文转成微信兼容的橙色品牌 HTML 排版，目标 < 35s。
"""
import json, sys, os, re, time
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
from _lib import call_deepseek, DEEPSEEK_MODEL


LAYOUT_SYSTEM = """你是微信公众号 HTML 排版专家，把文章正文转成微信兼容的橙色品牌排版 HTML。

严格遵守微信兼容规范：
- 全部 inline style，禁止 <style> 标签
- 禁止 flex / grid / rgba() / border-radius（微信不支持）
- 双列布局必须用 <table border="0">，td 必须有 style="border:none;"
- bgcolor 属性无效，必须用 style="background-color:"

品牌色：主橙 #FF5722，浅橙背景 #FFF3EE，分隔线 #FFE0D0

必须包含的组件：
1. 题图标签（橙色胶囊）：
   <p style="margin:0 0 16px;"><span style="background:#FF5722;color:#fff;font-size:13px;padding:4px 14px;border-radius:20px;font-weight:bold;">EasyClaw · 标签</span></p>

2. 小标题（橙色竖条）：
   <p style="margin:28px 0 14px;"><span style="display:inline-block;width:5px;height:20px;background:#FF5722;border-radius:3px;vertical-align:middle;margin-right:10px;"></span><span style="font-size:20px;font-weight:bold;color:#111;vertical-align:middle;">标题</span></p>

3. 左边框卡片（引用/故事）：
   <p style="background:#FFF3EE;border-left:5px solid #FF5722;padding:18px 20px;margin:16px 0;font-size:16px;line-height:1.9;">内容</p>

4. 金句卡片（橙底白字）：
   <p style="background:#FF5722;border-radius:10px;padding:20px 24px;text-align:center;margin:16px 0 24px;"><span style="font-size:20px;font-weight:bold;color:#fff;line-height:1.6;">"金句"</span></p>

5. 分隔线：
   <p style="border-top:1px solid #FFE0D0;margin:28px 0;">&nbsp;</p>

6. CTA结尾（橙底白按钮）：
   <p style="background:#FF5722;border-radius:14px;padding:36px 24px;text-align:center;margin-top:36px;">
     <span style="display:block;font-size:44px;margin-bottom:12px;">🦞</span>
     <span style="display:block;font-size:22px;font-weight:bold;color:#fff;margin-bottom:8px;">标题</span>
     <span style="display:block;font-size:15px;color:#FFE0D0;margin-bottom:20px;">副文案</span>
     <span style="display:inline-block;background:#fff;border-radius:30px;padding:12px 36px;font-size:17px;color:#FF5722;font-weight:bold;">立即体验</span>
   </p>

7. 标签行：
   <p style="margin-top:24px;font-size:13px;color:#FF5722;line-height:2.5;"><span style="background:#FFF3EE;padding:4px 12px;border-radius:20px;margin-right:6px;">#标签</span></p>

只输出 HTML，从 <!DOCTYPE html> 开始到 </html> 结束，不要任何解释或代码块标记。"""


def _layout_html(article_text, topic_title):
    prompt = (
        f"文章主题：{topic_title}\n\n"
        f"文章正文：\n{article_text}\n\n"
        "将以上文章转成完整的微信公众号排版 HTML。"
        "直接输出 HTML，从 <!DOCTYPE html> 开始。"
    )
    return call_deepseek(prompt, system=LAYOUT_SYSTEM, max_tokens=4000)


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

        article     = body.get("article", "")
        topic_title = body.get("topic_title", "")

        if not article:
            return self._json({"ok": False, "error": "article 不能为空"}, 400)

        try:
            t0 = time.time()
            raw_html = _layout_html(article, topic_title)
            html = _extract_html(raw_html)

            safe = topic_title[:30].replace("/", "-").replace("\\", "-").replace(" ", "_") or "wechat"
            filename = f"{safe}-wechat.html"
            self._json({
                "ok": True,
                "html": html,
                "filename": filename,
                "model": DEEPSEEK_MODEL,
                "elapsed_ms": int((time.time() - t0) * 1000),
            })
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
