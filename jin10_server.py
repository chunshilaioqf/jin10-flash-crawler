"""
金十数据实时快讯服务
- REST API: http://localhost:19999
- WebSocket: ws://localhost:19999/ws
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from playwright.async_api import async_playwright
import uvicorn


app = FastAPI(title="金十快讯服务", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局状态
messages: List[Dict] = []
websocket_clients: Set[WebSocket] = set()
running = False
browser = None
page = None


class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()
    
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)
    
    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)
    
    async def broadcast(self, message: Dict):
        dead = set()
        for ws in self.active:
            try:
                await ws.send_json(message)
            except:
                dead.add(ws)
        self.active -= dead


manager = ConnectionManager()


def decode_message(data: bytes) -> Dict | None:
    """解码二进制消息"""
    try:
        text = data.decode('utf-8', errors='ignore')
        json_start = text.find('{')
        if json_start < 0:
            return None
        
        json_text = text[json_start:]
        depth = 0
        end_pos = 0
        for i, c in enumerate(json_text):
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    end_pos = i + 1
                    break
        
        if end_pos > 0:
            return json.loads(json_text[:end_pos])
        return None
    except:
        return None


def extract_flash_content(data: Dict) -> Dict | None:
    """提取快讯内容"""
    try:
        if data.get("event") == "flash-hot-changed":
            items = data.get("data", [])
            for item in items:
                content = item.get("data", {}).get("content", "")
                if content:
                    return {
                        "id": item.get("id"),
                        "time": item.get("time"),
                        "content": content,
                        "important": item.get("important", 0),
                        "hot": item.get("hot", "")
                    }
        elif data.get("event") == "flash":
            d = data.get("data", {})
            return {
                "id": d.get("id"),
                "time": d.get("time"),
                "content": d.get("content", ""),
                "important": d.get("important", 0)
            }
        elif "content" in data:
            return {
                "id": data.get("id"),
                "time": data.get("time"),
                "content": data.get("content", ""),
                "important": data.get("important", 0)
            }
        return None
    except:
        return None


async def capture_loop():
    """持续抓取快讯"""
    global running, browser, page
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        def on_websocket(ws):
            def on_frame(payload):
                if isinstance(payload, bytes):
                    decoded = decode_message(payload)
                    if decoded:
                        flash = extract_flash_content(decoded)
                        if flash:
                            msg = {
                                "type": "flash",
                                "time": datetime.now().strftime("%H:%M:%S"),
                                "data": flash,
                                "raw": decoded
                            }
                            messages.append(msg)
                            # 只保留最近1000条
                            if len(messages) > 1000:
                                messages.pop(0)
                            # 广播给所有 WebSocket 客户端
                            asyncio.create_task(manager.broadcast(msg))
            
            ws.on("framereceived", on_frame)
        
        page.on("websocket", on_websocket)
        
        await page.goto("https://www.jin10.com/", wait_until="networkidle", timeout=30000)
        
        # 持续运行
        while running:
            await asyncio.sleep(1)
        
        await browser.close()


@app.on_event("startup")
async def startup():
    global running
    running = True
    asyncio.create_task(capture_loop())


@app.on_event("shutdown")
async def shutdown():
    global running
    running = False


# REST API
@app.get("/")
async def index():
    return {
        "name": "金十快讯服务",
        "version": "1.0.0",
        "endpoints": {
            "GET /api/messages": "获取历史消息",
            "GET /api/messages/latest": "获取最新消息",
            "GET /api/messages/count": "消息总数",
            "GET /api/status": "服务状态",
            "WS /ws": "实时推送"
        }
    }


@app.get("/api/messages")
async def get_messages(limit: int = 50, offset: int = 0):
    """获取历史消息"""
    total = len(messages)
    start = max(0, total - limit - offset)
    end = max(0, total - offset)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "messages": messages[start:end]
    }


@app.get("/api/messages/latest")
async def get_latest(limit: int = 10):
    """获取最新消息"""
    return {
        "messages": messages[-limit:] if messages else []
    }


@app.get("/api/messages/count")
async def get_count():
    """获取消息总数"""
    return {"count": len(messages)}


@app.get("/api/status")
async def get_status():
    """获取服务状态"""
    return {
        "running": running,
        "message_count": len(messages),
        "websocket_clients": len(manager.active),
        "uptime": datetime.now().isoformat()
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket 实时推送"""
    await manager.connect(ws)
    try:
        # 发送最近的消息
        if messages:
            await ws.send_json({
                "type": "history",
                "messages": messages[-20:]
            })
        
        # 保持连接
        while True:
            try:
                data = await ws.receive_text()
                # 可以处理客户端消息
            except WebSocketDisconnect:
                break
    finally:
        manager.disconnect(ws)


if __name__ == "__main__":
    print("=== 金十快讯服务 ===")
    print("REST API: http://localhost:19999")
    print("WebSocket: ws://localhost:19999/ws")
    print("")
    uvicorn.run(app, host="0.0.0.0", port=19999)