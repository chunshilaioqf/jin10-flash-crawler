"""
金十数据实时快讯服务 (稳定版)
"""

import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict, Set, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn


app = FastAPI(title="金十快讯服务", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

messages: List[Dict] = []
MAX_MESSAGES = 1000
running = False


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


def decode_message(data: bytes) -> Optional[Dict]:
    try:
        text = data.decode('utf-8', errors='ignore')
        start = text.find('{')
        if start < 0:
            return None
        json_text = text[start:]
        depth = 0
        end = 0
        for i, c in enumerate(json_text):
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end > 0:
            return json.loads(json_text[:end])
        return None
    except:
        return None


def extract_flash(data: Dict) -> Optional[Dict]:
    try:
        if data.get("event") == "flash-hot-changed":
            for item in data.get("data", []):
                content = item.get("data", {}).get("content", "")
                if content:
                    content = re.sub(r'<[^>]+>', '', content)
                    return {
                        "id": item.get("id"),
                        "time": item.get("time"),
                        "content": content,
                        "important": item.get("important", 0),
                        "hot": item.get("hot", "")
                    }
        elif data.get("event") == "flash":
            d = data.get("data", {})
            content = d.get("content", "")
            if content:
                content = re.sub(r'<[^>]+>', '', content)
                return {"id": d.get("id"), "time": d.get("time"), "content": content, "important": d.get("important", 0)}
        elif "content" in data:
            content = data.get("content", "")
            if content:
                content = re.sub(r'<[^>]+>', '', content)
                return {"id": data.get("id"), "time": data.get("time"), "content": content, "important": data.get("important", 0)}
        return None
    except:
        return None


async def capture_with_playwright():
    global running
    
    print("[抓取器] 启动...")
    
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[抓取器] 错误: pip install playwright")
        return
    
    while running:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                page_messages = []
                
                def on_websocket(ws):
                    def on_frame(payload):
                        if isinstance(payload, bytes):
                            decoded = decode_message(payload)
                            if decoded:
                                flash = extract_flash(decoded)
                                if flash:
                                    page_messages.append(flash)
                    ws.on("framereceived", on_frame)
                
                page.on("websocket", on_websocket)
                
                print("[抓取器] 连接金十...")
                await page.goto("https://www.jin10.com/", wait_until="networkidle", timeout=30000)
                print("[抓取器] 已连接，监听30秒...")
                
                await asyncio.sleep(30)
                
                for flash in page_messages:
                    msg = {"type": "flash", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "data": flash}
                    messages.append(msg)
                    if len(messages) > MAX_MESSAGES:
                        messages.pop(0)
                    await manager.broadcast(msg)
                    print(f"[快讯] {flash.get('content', '')[:80]}")
                
                print(f"[抓取器] 本轮捕获 {len(page_messages)} 条")
                
                await browser.close()
                await asyncio.sleep(2)
                
        except Exception as e:
            print(f"[抓取器] 错误: {e}")
            await asyncio.sleep(5)


@app.on_event("startup")
async def startup():
    global running
    running = True
    asyncio.create_task(capture_with_playwright())


@app.on_event("shutdown")
async def shutdown():
    global running
    running = False


@app.get("/")
async def index():
    return {"name": "金十快讯服务", "version": "1.0.0", "status": "running" if running else "stopped", "messages": len(messages), "endpoints": {"GET /api/messages": "历史消息", "GET /api/messages/latest": "最新消息", "GET /api/status": "状态", "WS /ws": "实时推送"}}

@app.get("/api/messages")
async def get_messages(limit: int = 50):
    return {"count": len(messages), "messages": messages[-limit:]}

@app.get("/api/messages/latest")
async def get_latest(limit: int = 10):
    return {"messages": messages[-limit:] if messages else []}

@app.get("/api/messages/count")
async def get_count():
    return {"count": len(messages)}

@app.get("/api/status")
async def get_status():
    return {"running": running, "message_count": len(messages), "websocket_clients": len(manager.active), "time": datetime.now().isoformat()}

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        if messages:
            await ws.send_json({"type": "history", "messages": messages[-20:]})
        while True:
            try:
                await ws.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        manager.disconnect(ws)


if __name__ == "__main__":
    print("=" * 50)
    print("  金十快讯实时服务")
    print("=" * 50)
    print(f"  REST API: http://localhost:19999")
    print(f"  WebSocket: ws://localhost:19999/ws")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=19999)
