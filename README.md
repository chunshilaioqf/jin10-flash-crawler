# 金十数据实时快讯抓取器

实时抓取金十数据 (jin10.com) 的快讯消息，提供 REST API 和 WebSocket 实时推送。

## 安装依赖

```bash
pip install fastapi uvicorn playwright
python3 -m playwright install chromium
```

## 启动服务

```bash
python3 jin10_server.py
```

服务运行在端口 **19999**

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | API 文档 |
| `/api/messages` | GET | 获取历史消息 |
| `/api/messages/latest` | GET | 获取最新消息 |
| `/api/messages/count` | GET | 消息总数 |
| `/api/status` | GET | 服务状态 |
| `/ws` | WebSocket | 实时推送 |

## 使用示例

### REST API

```bash
# 获取最新5条消息
curl http://localhost:19999/api/messages/latest?limit=5

# 获取服务状态
curl http://localhost:19999/api/status

# 获取消息总数
curl http://localhost:19999/api/messages/count
```

### WebSocket

```javascript
const ws = new WebSocket('ws://localhost:19999/ws');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'flash') {
        console.log(data.data.content);
    } else if (data.type === 'history') {
        console.log('历史消息:', data.messages);
    }
};
```

### Python

```python
import asyncio
import websockets
import json

async def listen():
    async with websockets.connect('ws://localhost:19999/ws') as ws:
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            if data['type'] == 'flash':
                print(f"[{data['data']['time']}] {data['data']['content']}")

asyncio.run(listen())
```

## 消息格式

```json
{
  "type": "flash",
  "time": "2026-03-31 15:49:39",
  "data": {
    "id": "20260331154939123456",
    "time": "2026-03-31 15:49:39",
    "content": "快讯内容...",
    "important": 0,
    "hot": "火"
  }
}
```

## 其他脚本

### Playwright 抓取器

```bash
python3 jin10_playwright.py 30  # 抓取30秒
```

### WebSocket 客户端

```bash
python3 jin10_client.py 30  # 监听30秒
```

## 配置说明

- **轮询间隔**: 5秒（可在 `jin10_server.py` 中修改）
- **最大消息数**: 1000条
- **消息去重**: 自动
- **持久化**: 保存到 `jin10_messages.json`

## 注意事项

- 仅供学习研究使用
- 请遵守金十数据的使用条款
- 建议在本地运行
- 使用 Playwright 需要 Chrome/Chromium

## 文件说明

| 文件 | 说明 |
|------|------|
| `jin10_server.py` | 主服务（推荐） |
| `jin10_playwright.py` | Playwright 抓取器 |
| `jin10_client.py` | WebSocket 客户端 |
| `jin10_monitor.py` | 消息监控器 |

## License

MIT