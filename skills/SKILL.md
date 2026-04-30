---
name: 星辰风格公众号推文
description: 【星辰风格公众号推文】公众号推文创作 + 橙色品牌排版 HTML 生成。触发词：写公众号文章、公众号推文、微信公众号、公众号排版、星辰风格。支持活动回顾、产品介绍、干货分享等类型，自动生成可粘贴进微信公众平台的兼容 HTML。含完整橙色组件库（金句卡、数据卡、人物卡、序号列表等）。
---

# 公众号推文 Skill

## 工作流程

### Step 1：理解需求
收集以下信息（没有的跳过）：
- **文章类型**：活动回顾 / 产品介绍 / 干货分享 / 其他
- **素材内容**：用户提供的原始信息、事件经过、数据
- **风格要求**：亲切简洁 / 专业严肃 / 活泼有趣
- **是否需要排版 HTML**：默认生成

### Step 2：写文章
按文章类型套用对应模板，见 `references/article-templates.md`

### Step 3：生成 HTML
按微信兼容规范生成排版 HTML（规范见下方）

### Step 4：发送文件
用飞书 API 发送 HTML 文件到当前群，**不要只说"已生成"**。

---

## 写作原则

- **只要结果，不要过程**：开门见山，不废话
- **干货嵌进叙事**：干货不单独堆列，融入故事节奏
- **有梗就用**：现场金句、有趣瞬间优先放开头
- **结尾必须有 CTA**：关注 / 报名 / 评论区互动

---

## 🎨 排版风格规范（2026-03-15 定稿，龙虾局深圳场验证）

### 主色调
- **橙色**：`#FF5722`（主色）、`#FFF3EE`（浅橙背景）、`#FFE0D0`（分隔线）
- 橙色贯穿全文：标签、小标题竖条、左边框卡片、金句卡、数据卡、CTA

### 整体结构
```
题图标签（橙色胶囊）
标题 + 副标题
↓
图片占位 + 正文段落（交替出现）
↓
[分隔线] ← 每大段之间用 border-top:#FFE0D0
↓
小标题（橙色竖条 + 加粗文字）
↓
内容段落 / 卡片 / 数据块
↓
[分隔线]
↓
CTA（橙色背景，白色按钮）
↓
标签行（浅橙圆角胶囊）
```

### 核心组件（微信兼容写法）

#### 1. 题图标签
```html
<p style="margin:0 0 16px;">
  <span style="background:#FF5722;color:#fff;font-size:13px;padding:4px 14px;border-radius:20px;font-weight:bold;">EasyClaw · 2026-0314 📍深圳</span>
</p>
```

#### 2. 小标题（橙色竖条）
```html
<p style="margin:28px 0 14px;">
  <span style="display:inline-block;width:5px;height:20px;background:#FF5722;border-radius:3px;vertical-align:middle;margin-right:10px;"></span>
  <span style="font-size:20px;font-weight:bold;color:#111;vertical-align:middle;">小标题文字</span>
</p>
```

#### 3. 橙色左边框卡片（引用 / 故事 / 提示）
```html
<p style="background:#FFF3EE;border-left:5px solid #FF5722;padding:18px 20px;margin:16px 0;border-radius:0 8px 8px 0;font-size:16px;line-height:1.9;">
  内容文字
</p>
```

#### 4. 金句卡片（橙底白字）
```html
<p style="background:#FF5722;border-radius:10px;padding:20px 24px;text-align:center;margin:16px 0 24px;">
  <span style="font-size:20px;font-weight:bold;color:#fff;line-height:1.6;">"金句内容"</span>
</p>
```

#### 5. 数据双列卡（用 table，必须用 style 而非 bgcolor）
```html
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:20px 0;border-radius:12px;overflow:hidden;">
  <tr>
    <td width="50%" style="background-color:#FF5722;padding:24px 16px;text-align:center;color:#fff;">
      <div style="font-size:48px;font-weight:bold;line-height:1.1;color:#fff;">60%</div>
      <div style="font-size:14px;margin-top:6px;color:#fff;">整体提效</div>
    </td>
    <td width="2" style="background-color:#E64A19;padding:0;">&nbsp;</td>
    <td width="50%" style="background-color:#FF5722;padding:24px 16px;text-align:center;color:#fff;">
      <div style="font-size:36px;font-weight:bold;line-height:1.1;color:#fff;">2h→10min</div>
      <div style="font-size:14px;margin-top:6px;color:#fff;">每日工作时长</div>
    </td>
  </tr>
</table>
```

#### 6. 人物介绍卡
```html
<p style="background:#FFF8F5;border-left:5px solid #FF5722;padding:14px 18px;margin:16px 0;border-radius:0 8px 8px 0;">
  <span style="font-size:22px;vertical-align:middle;margin-right:10px;">🐆</span>
  <strong style="font-size:16px;color:#111;vertical-align:middle;">姓名 · 称谓</strong><br>
  <span style="font-size:13px;color:#FF5722;padding-left:34px;display:block;margin-top:4px;">职位头衔</span>
</p>
```

#### 7. 带序号列表（橙色圆形序号）
```html
<p style="background:#FFF8F5;padding:20px 20px 4px;margin:16px 0;border-radius:10px;border-left:5px solid #FF5722;">
  <span style="display:inline-block;width:24px;height:24px;background:#FF5722;border-radius:50%;text-align:center;line-height:24px;color:#fff;font-size:13px;font-weight:bold;vertical-align:middle;margin-right:10px;">1</span>
  <strong style="vertical-align:middle;">条目标题</strong><br>
  <span style="color:#888;font-size:14px;padding-left:34px;display:block;margin-bottom:14px;">条目说明</span>
  <!-- 重复 2、3 ... -->
</p>
```

#### 8. 图片占位符（不加任何边框）
```html
<p style="margin:16px 0 6px;text-align:center;color:#ccc;font-size:14px;">📸 插入：图片说明</p>
<p style="text-align:center;font-size:13px;color:#aaa;margin:0 0 20px;">▲ 图注文字</p>
```

#### 9. 分隔线
```html
<p style="border-top:1px solid #FFE0D0;margin:28px 0;">&nbsp;</p>
```

#### 10. CTA 结尾块（橙底白按钮）
```html
<p style="background:#FF5722;border-radius:14px;padding:36px 24px;text-align:center;margin-top:36px;">
  <span style="display:block;font-size:44px;margin-bottom:12px;">🦞</span>
  <span style="display:block;font-size:22px;font-weight:bold;color:#fff;margin-bottom:8px;">标题</span>
  <span style="display:block;font-size:15px;color:#ffe0d0;margin-bottom:20px;">副文案</span>
  <span style="display:inline-block;background:#fff;border-radius:30px;padding:12px 36px;font-size:17px;color:#FF5722;font-weight:bold;">按钮文字</span>
  <span style="display:block;margin-top:18px;font-size:14px;color:#ffd0c0;">互动引导语</span>
</p>
```

#### 11. 标签行
```html
<p style="margin-top:24px;font-size:13px;color:#FF5722;line-height:2.5;">
  <span style="background:#FFF3EE;padding:4px 12px;border-radius:20px;margin-right:6px;">#标签</span>
</p>
```

---

## ⚠️ 微信编辑器兼容禁忌（踩坑总结）

| 禁止 | 原因 | 替代方案 |
|------|------|--------|
| `border-left` 在 CSS class 里 | 微信不渲染 class | 全部用 inline style |
| `bgcolor="#FF5722"` | 微信不认 HTML 属性 | 改用 `style="background-color:#FF5722"` |
| `rgba(255,255,255,0.8)` | 微信不支持 rgba | 改用纯十六进制 `#ffe0d0` |
| `display:flex` | 微信不支持 flex | 改用 `<table>` 双列布局 |
| `<table>` 不加 `border="0"` | 微信会渲染默认边框 | 必须加 `border="0"` |
| `<style>` 标签内的样式 | 微信粘贴时会丢失 | 全部 inline style |
| `border:1px dashed` 在图片占位 | 会显示奇怪虚线框 | 去掉边框，只用浅色文字提示 |

---

## 飞书 API 发文件（标准流程）

```python
import requests, json
APP_ID = "cli_a9157980e3781cd9"
APP_SECRET = "n3FlU0HHYTRTo8qfYScEMdPykjEygHNc"

token = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET}).json()["tenant_access_token"]

with open("/path/to/file.html", "rb") as f:
    file_key = requests.post("https://open.feishu.cn/open-apis/im/v1/files",
        headers={"Authorization": f"Bearer {token}"},
        data={"file_type": "stream", "file_name": "article.html"},
        files={"file": f}).json()["data"]["file_key"]

requests.post("https://open.feishu.cn/open-apis/im/v1/messages",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    params={"receive_id_type": "chat_id"},
    json={"receive_id": "<chat_id>", "msg_type": "file",
          "content": json.dumps({"file_key": file_key})})
```
