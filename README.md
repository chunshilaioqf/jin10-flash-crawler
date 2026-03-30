# 金十数据实时快讯抓取器

实时抓取金十数据 (jin10.com) 的快讯消息。

## 安装依赖

```bash
pip install playwright
python3 -m playwright install chromium
```

## 使用方法

```bash
# 默认监听30秒
python3 jin10_playwright.py

# 自定义监听时长（秒）
python3 jin10_playwright.py 60
```

## 输出示例

```
=== 金十快讯抓取器 ===

正在连接金十数据...
✅ 已连接
监听 30 秒...

🔥 美国白宫：特朗普未排除对伊朗进行地面行动的可能性。
📰 金十数据3月31日讯，美联储主席鲍威尔...

共捕获 5 条消息
已保存到 jin10_20260331_014500.json
```

## 数据格式

捕获的消息保存为 JSON 格式：

```json
{
  "time": "01:44:41",
  "type": "flash",
  "data": {
    "event": "flash-hot-changed",
    "data": [{
      "time": "2026-03-31 01:44:41",
      "data": {
        "content": "快讯内容...",
        "source": "来源"
      }
    }]
  }
}
```

## 文件说明

- `jin10_playwright.py` - 推荐使用，通过浏览器引擎抓取，最稳定
- `jin10_client.py` - 直接 WebSocket 连接版（可能不稳定）

## 注意事项

- 仅供学习研究使用
- 请遵守金十数据的使用条款
- 建议在本地运行，不要频繁请求