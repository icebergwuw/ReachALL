# 微信公众号 HTML 兼容指南

## 核心原则

微信公众平台自带编辑器对 HTML 限制严格：
- ✅ 支持：`<table>`、`<p>`、`<strong>`、`<span>`、`<hr>`、内联 `style`
- ❌ 不支持：`flex`、`grid`、`border-radius`、CSS 渐变、`<style>` 标签
- ⚠️ `<table>` 默认有边框，必须显式消除

## 必须加的属性

```html
<!-- 每个 table 必须有 -->
<table border="0" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;border:0 none;">

<!-- 每个 td 必须有 -->
<td style="border:none; ...其他样式...">
```

## 颜色规范（EasyClaw 品牌色）

- 主橙色：`#ff6b1a`
- 浅橙背景：`#fff8f3`
- 更浅橙背景：`#fff3e8`
- 边框橙：`#ffba80`
- 分隔线：`#ffd4a8`

## 常用组件写法

### 标题块（橙色）
```html
<table width="100%" border="0" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;border:0 none;margin:24px 0 28px;">
  <tr>
    <td style="border:none;background-color:#ff6b1a;padding:32px 24px;text-align:center;">
      <p style="margin:0;font-size:20px;font-weight:700;color:#fff;">标题文字</p>
    </td>
  </tr>
</table>
```

### 左色条小标题
```html
<table width="100%" border="0" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;border:0 none;margin:0 0 14px;">
  <tr>
    <td width="5" style="border:none;background-color:#ff6b1a;">&nbsp;</td>
    <td style="border:none;padding-left:10px;font-size:18px;font-weight:700;color:#111;">小标题</td>
  </tr>
</table>
```

### 引用块
```html
<table width="100%" border="0" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;border:0 none;margin:16px 0;">
  <tr>
    <td style="border:none;border-left:4px solid #ff6b1a;background-color:#fff8f3;padding:14px 18px;color:#555;">
      引用内容
    </td>
  </tr>
</table>
```

### 高亮框（梗/金句）
```html
<table width="100%" border="0" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;border:0 none;margin:16px 0;">
  <tr>
    <td style="border:none;border-left:4px solid #ff6b1a;background-color:#fff3e8;padding:20px;text-align:center;">
      <p style="margin:0 0 8px;font-size:26px;font-weight:800;color:#ff6b1a;letter-spacing:5px;">关键词</p>
      <p style="margin:0;font-size:13px;color:#999;">副标注</p>
    </td>
  </tr>
</table>
```

### 数据卡片（4列）
```html
<table width="100%" border="0" cellpadding="0" cellspacing="6"
       style="border-collapse:separate;border:0 none;margin:16px 0;">
  <tr>
    <td width="25%" style="border:none;background-color:#fff8f3;padding:14px 8px;text-align:center;">
      <p style="margin:0;font-size:20px;font-weight:800;color:#ff6b1a;">数据</p>
      <p style="margin:4px 0 0;font-size:12px;color:#999;">说明</p>
    </td>
    <!-- 重复 td ... -->
  </tr>
</table>
```

### 编号干货列表
```html
<table width="100%" border="0" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;border:0 none;margin-bottom:18px;">
  <tr>
    <td width="36" valign="top" style="border:none;padding-top:2px;">
      <table border="0" cellpadding="0" cellspacing="0"
             style="border-collapse:collapse;border:0 none;">
        <tr>
          <td style="border:none;width:28px;height:28px;background-color:#ff6b1a;
                     color:#fff;font-size:14px;font-weight:700;
                     text-align:center;line-height:28px;">①</td>
        </tr>
      </table>
    </td>
    <td style="border:none;padding-left:10px;">
      <p style="margin:0 0 6px;font-size:15px;font-weight:700;color:#222;">标题</p>
      <p style="margin:0;font-size:14px;color:#666;line-height:1.75;">内容</p>
    </td>
  </tr>
</table>
```

### 分隔线
```html
<hr style="border:none;border-top:1px solid #ffd4a8;margin:24px 0;">
```

### CTA 结尾卡片
```html
<table width="100%" border="0" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;border:1px solid #ffba80;margin-top:32px;">
  <tr>
    <td style="border:none;background-color:#fff3e8;padding:28px 20px;text-align:center;">
      <p style="margin:0 0 8px;font-size:28px;">🦞</p>
      <p style="margin:0 0 8px;font-size:18px;font-weight:700;color:#222;">标题</p>
      <p style="margin:0 0 10px;font-size:19px;font-weight:800;color:#ff6b1a;">关键信息</p>
      <p style="margin:0;font-size:13px;color:#999;">easyclaw.com</p>
    </td>
  </tr>
</table>
```

## 文件命名规范

`文章主题-wechat.html`，保存到 workspace 根目录，生成后立即用飞书 API 发送。
