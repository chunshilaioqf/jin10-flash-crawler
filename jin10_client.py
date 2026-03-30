"""
金十数据 WebSocket 实时快讯抓取器
用法: python3 jin10_client.py [监听秒数]
"""

import asyncio
import websockets
import json
import re
import sys
from datetime import datetime


async def capture_jin10(duration=30):
    """捕获金十快讯"""
    
    messages = []
    
    try:
        # 连接快讯 WebSocket
        ws = await websockets.connect(
            "wss://wss-flash-2.jin10.com/",
            origin="https://www.jin10.com"
        )
        
        # 发送初始化
        await ws.send(b'\x00\x01')
        init_resp = await ws.recv()
        print(f"✅ 已连接金十快讯 WebSocket")
        
        # 监听消息
        end_time = asyncio.get_event_loop().time() + duration
        heartbeat_counter = 0
        
        while asyncio.get_event_loop().time() < end_time:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=2)
                
                if isinstance(msg, bytes) and len(msg) > 10:
                    # 尝试提取 JSON
                    decoded = decode_jin10_message(msg)
                    if decoded:
                        messages.append({
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "data": decoded
                        })
                        print_message(decoded)
                
                heartbeat_counter += 1
                if heartbeat_counter % 5 == 0:
                    await ws.send(b'\x00\x01')
                    
            except asyncio.TimeoutError:
                await ws.send(b'\x00\x01')
            except websockets.exceptions.ConnectionClosed:
                print("连接断开，尝试重连...")
                ws = await websockets.connect(
                    "wss://wss-flash-2.jin10.com/",
                    origin="https://www.jin10.com"
                )
                await ws.send(b'\x00\x01')
                await ws.recv()
        
        await ws.close()
        
    except Exception as e:
        print(f"错误: {e}")
    
    return messages


def decode_jin10_message(data: bytes):
    """解码金十 WebSocket 消息"""
    try:
        # 查找 JSON 开始位置
        text = data.decode('utf-8', errors='ignore')
        
        # 查找 { 开始的位置
        json_start = text.find('{')
        if json_start < 0:
            return None
        
        # 提取 JSON
        json_text = text[json_start:]
        
        # 找到匹配的 }
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
            json_str = json_text[:end_pos]
            try:
                return json.loads(json_str)
            except:
                pass
        
        return None
    except:
        return None


def print_message(data):
    """打印消息"""
    try:
        if isinstance(data, dict):
            # 快讯热点
            if data.get("event") == "flash-hot-changed":
                for item in data.get("data", []):
                    content = item.get("data", {}).get("content", "")
                    if content:
                        print(f"🔥 {content[:100]}")
            
            # 普通快讯
            elif data.get("event") == "flash":
                content = data.get("data", {}).get("content", "")
                if content:
                    print(f"📰 {content[:100]}")
            
            # 直接包含 content
            elif "content" in data:
                print(f"📰 {data['content'][:100]}")
    except:
        pass


def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    print(f"开始抓取金十快讯 ({duration}秒)...\n")
    
    messages = asyncio.run(capture_jin10(duration))
    
    print(f"\n共捕获 {len(messages)} 条消息")
    
    # 保存到文件
    if messages:
        with open("jin10_messages.json", "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        print(f"消息已保存到 jin10_messages.json")


if __name__ == "__main__":
    main()