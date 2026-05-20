"""
POST /api/generate/wechat/article  (Step 1 of 2)
Body: { topic_title, topic_heat, topic_platform, extra }
Returns: { ok, article, model }

仅生成正文（傅盛风格 markdown），目标 < 25s。
前端再调 /api/generate/wechat/layout 把正文转 HTML。
"""
import json, sys, os, time
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
from _lib import call_deepseek, DEEPSEEK_MODEL


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
- 短句多换行，段落 3-5 行
- 数据要具体（"14天"比"两周"有力）

文章结构：
① 痛点开场：用一个真实场景引入读者最头疼的问题（100字左右）
② 产品介绍：一句话说清 EasyClaw 是什么
③ 3-4 个核心价值点：用故事包裹，不是功能列表
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


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")

        topic_title    = body.get("topic_title", "")
        topic_heat     = body.get("topic_heat", "")
        topic_platform = body.get("topic_platform", "weibo")
        extra          = body.get("extra", "")

        try:
            t0 = time.time()
            article = _write_article(topic_title, topic_heat, topic_platform, extra)
            self._json({
                "ok": True,
                "article": article,
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
