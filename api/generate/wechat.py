"""
POST /api/generate/wechat
Body: { topic_title, topic_heat, topic_platform, extra }
Returns: { ok, html, filename }
"""
import json, sys, os, re
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
from _lib import call_minimax

# ── 傅盛写作风格（文章内容） ───────────────────────────────────────────────────
WRITING_STYLE = """
## 写作风格：傅盛风格
- 口语化：像跟朋友聊天，不是学术论文
- 故事感：用具体事例代替空洞理论
- 有态度：表达观点，不做和稀泥
- 简化复杂：善用类比让难懂的东西变简单
- 短句多换行：段落3-5行，多空行，不堆砌
- 直接说观点：不模棱两可，不说"有人认为...也有人认为"
- 数据适度：2-3个数据点，用故事包裹数字

## 文章结构（产品介绍型）
① 痛点开场：读者最头疼的问题，用故事或场景引入（100-150字）
② 产品是什么：一句话定义 EasyClaw
③ 核心功能：3-5个，用故事包裹，不是功能列表
④ 真实感案例：具体场景，有细节，有数据
⑤ CTA：下载/试用/关注

## 标题策略
优先用：
- 悬念式：「我为什么放弃了...」
- 反问式：「你真的了解...吗？」
- 对比式：「...vs...，差在哪里」
避免：直接给结论的结论式标题
"""

# ── 星辰排版规范（HTML 组件库） ───────────────────────────────────────────────
HTML_GUIDE = """
## 微信 HTML 兼容规范（严格遵守）

### 禁止使用
- display:flex / display:grid
- border-radius（微信会忽略）
- rgba() 颜色（改用十六进制）
- <style> 标签（粘贴后丢失）
- bgcolor 属性（改用 style="background-color:"）
- table 不加 border="0"（会出现默认边框）

### 必须使用 inline style，所有样式写在 style="" 里

### 品牌色
- 主橙：#FF5722
- 浅橙背景：#FFF3EE
- 分隔线色：#FFE0D0

### 核心组件

#### 题图标签（橙色胶囊）
<p style="margin:0 0 16px;">
  <span style="background:#FF5722;color:#fff;font-size:13px;padding:4px 14px;border-radius:20px;font-weight:bold;">EasyClaw · 热点话题</span>
</p>

#### 小标题（橙色竖条）
<p style="margin:28px 0 14px;">
  <span style="display:inline-block;width:5px;height:20px;background:#FF5722;border-radius:3px;vertical-align:middle;margin-right:10px;"></span>
  <span style="font-size:20px;font-weight:bold;color:#111;vertical-align:middle;">小标题文字</span>
</p>

#### 橙色左边框卡片（引用/故事/提示）
<p style="background:#FFF3EE;border-left:5px solid #FF5722;padding:18px 20px;margin:16px 0;font-size:16px;line-height:1.9;">
  内容文字
</p>

#### 金句卡片（橙底白字）
<p style="background:#FF5722;border-radius:10px;padding:20px 24px;text-align:center;margin:16px 0 24px;">
  <span style="font-size:20px;font-weight:bold;color:#fff;line-height:1.6;">"金句内容"</span>
</p>

#### 数据双列卡（必须用 table）
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:20px 0;">
  <tr>
    <td width="49%" style="border:none;background-color:#FF5722;padding:24px 16px;text-align:center;">
      <div style="font-size:48px;font-weight:bold;line-height:1.1;color:#fff;">60%</div>
      <div style="font-size:14px;margin-top:6px;color:#fff;">整体提效</div>
    </td>
    <td width="2%" style="border:none;background-color:#E64A19;padding:0;">&nbsp;</td>
    <td width="49%" style="border:none;background-color:#FF5722;padding:24px 16px;text-align:center;">
      <div style="font-size:36px;font-weight:bold;line-height:1.1;color:#fff;">2h→10min</div>
      <div style="font-size:14px;margin-top:6px;color:#fff;">每日工作时长</div>
    </td>
  </tr>
</table>

#### 带序号列表（橙色圆形序号）
<p style="background:#FFF8F5;padding:20px 20px 4px;margin:16px 0;border-left:5px solid #FF5722;">
  <span style="display:inline-block;width:24px;height:24px;background:#FF5722;border-radius:50%;text-align:center;line-height:24px;color:#fff;font-size:13px;font-weight:bold;vertical-align:middle;margin-right:10px;">1</span>
  <strong style="vertical-align:middle;">条目标题</strong><br>
  <span style="color:#888;font-size:14px;padding-left:34px;display:block;margin-bottom:14px;">条目说明</span>
</p>

#### 分隔线
<p style="border-top:1px solid #FFE0D0;margin:28px 0;">&nbsp;</p>

#### CTA 结尾块（橙底白按钮）
<p style="background:#FF5722;border-radius:14px;padding:36px 24px;text-align:center;margin-top:36px;">
  <span style="display:block;font-size:44px;margin-bottom:12px;">🦞</span>
  <span style="display:block;font-size:22px;font-weight:bold;color:#fff;margin-bottom:8px;">标题</span>
  <span style="display:block;font-size:15px;color:#FFE0D0;margin-bottom:20px;">副文案</span>
  <span style="display:inline-block;background:#fff;border-radius:30px;padding:12px 36px;font-size:17px;color:#FF5722;font-weight:bold;">按钮文字</span>
  <span style="display:block;margin-top:18px;font-size:14px;color:#FFD0C0;">互动引导语</span>
</p>

#### 标签行
<p style="margin-top:24px;font-size:13px;color:#FF5722;line-height:2.5;">
  <span style="background:#FFF3EE;padding:4px 12px;border-radius:20px;margin-right:6px;">#标签</span>
</p>
"""

SYSTEM_PROMPT = f"""你是 EasyClaw 品牌微信公众号的资深内容运营。

EasyClaw 是猎豹移动出品的桌面 AI Agent 工具：
- 无代码零配置，Mac/Windows 一键安装
- 本地沙盒运行，数据不上传
- 通过微信/飞书/WhatsApp 远程控制电脑
- 自动化处理文件、内容发布、日程管理等重复工作

{WRITING_STYLE}

{HTML_GUIDE}
"""


def _build_prompt(body: dict) -> str:
    topic_title    = body.get("topic_title", "")
    topic_heat     = body.get("topic_heat", "")
    topic_platform = body.get("topic_platform", "weibo")
    extra          = body.get("extra", "")

    return (
        f"当前热点话题：「{topic_title}」（热度：{topic_heat}，来源平台：{topic_platform}）\n"
        + (f"额外要求：{extra}\n" if extra else "")
        + """
任务：基于以上热点，用傅盛风格写一篇 EasyClaw 公众号推文，并按星辰排版规范生成完整 HTML。

严格要求：
1. 只输出 HTML，第一个字符是 <，最后一个字符是 >
2. 完整结构：<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body>...</body></html>
3. 全部 inline style，禁止 flex/grid，禁止 <style> 标签
4. 双列布局必须用 table，table 必须有 border="0"
5. 不输出任何解释文字或 markdown，直接输出纯 HTML

现在直接输出 HTML："""
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
            raw = call_minimax(prompt, system=SYSTEM_PROMPT, max_tokens=8192)
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
