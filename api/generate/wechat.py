"""
POST /api/generate/wechat
Body: { topic_title, topic_heat, topic_platform, extra }
Returns: { ok, html, filename }

两步生成：
  Step 1 — 用傅盛风格写文章正文（max_tokens=2000，~15s）
  Step 2 — 把正文转成星辰排版 HTML（max_tokens=4000，~25s）
  合计 < 60s，在 Vercel Hobby 超时限制内
"""
import json, sys, os, re
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
from _lib import call_deepseek, DEEPSEEK_MODEL

# ── Step 1：傅盛风格写文章 ────────────────────────────────────────────────────
WRITE_SYSTEM = """你是 EasyClaw 品牌微信公众号主笔，用傅盛写作风格创作推文。

EasyClaw 是猎豹移动出品的桌面 AI Agent 工具：
- 无代码零配置，Mac/Windows 一键安装
- 本地沙盒，数据不上传
- 手机远程控制电脑（微信/飞书/WhatsApp 发指令）
- 自动化处理文件、内容发布、日程管理等重复工作

写作风格要求：
- 口语化，像跟朋友聊天
- 故事感，用具体场景代替空洞理论
- 有态度，直接说观点，不和稀泥
- 短句多换行，段落3-5行
- 数据要具体（"14天"比"两周"有力）

文章结构：
① 痛点开场：用一个真实场景引入读者最头疼的问题（100字左右）
② 产品介绍：一句话说清 EasyClaw 是什么
③ 3-4个核心价值点：用故事包裹，不是功能列表
④ 金句：一句能让人转发的话
⑤ CTA：引导关注/下载，自然不硬广

只输出文章正文，不要标题之外的任何格式标记。"""


def _write_article(topic_title, topic_heat, topic_platform, extra):
    prompt = (
        f"热点话题：「{topic_title}」（热度：{topic_heat}，来源：{topic_platform}）\n"
        + (f"额外要求：{extra}\n" if extra else "")
        + "\n用傅盛风格，基于这个热点写一篇 EasyClaw 公众号推文正文。"
        "开门见山，有故事，有态度，结尾有 CTA。直接输出正文，不加任何说明。"
    )
    return call_deepseek(prompt, system=WRITE_SYSTEM, max_tokens=2000)


# ── Step 2：转成星辰排版 HTML ─────────────────────────────────────────────────
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


# ── HTML 提取 ─────────────────────────────────────────────────────────────────
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

        topic_title    = body.get("topic_title", "")
        topic_heat     = body.get("topic_heat", "")
        topic_platform = body.get("topic_platform", "weibo")
        extra          = body.get("extra", "")

        try:
            # Step 1: 写文章正文
            article = _write_article(topic_title, topic_heat, topic_platform, extra)
            # Step 2: 转排版 HTML
            raw_html = _layout_html(article, topic_title)
            html = _extract_html(raw_html)

            safe = topic_title[:30].replace("/", "-").replace("\\", "-").replace(" ", "_")
            filename = f"{safe}-wechat.html"
            self._json({"ok": True, "html": html, "filename": filename, "model": DEEPSEEK_MODEL})
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
