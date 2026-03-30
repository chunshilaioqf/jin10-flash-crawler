"""
金十数据实时快讯抓取器 (Playwright 版)
用法: python3 jin10_playwright.py [监听秒数]

依赖: pip install playwright && python3 -m playwright install chromium
"""

import asyncio
import json
import sys
from datetime import datetime
from playwright.async_api import async_playwright


async def capture_jin10_flash(duration=30):
    """使用 Playwright 捕获金十快讯"""
    
    messages = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 监听 WebSocket
        def on_websocket(ws):
            def on_frame(payload):
                if isinstance(payload, bytes):
                    decoded = decode_message(payload)
                    if decoded:
                        msg = {
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "type": "flash",
                            "data": decoded
                        }
                        messages.append(msg)
                        print_message(decoded)
            
            ws.on("framereceived", on_frame)
        
        page.on("websocket", on_websocket)
        
        # 访问金十
        print("正在连接金十数据...")
        await page.goto("https://www.jin10.com/", wait_until="networkidle", timeout=30000)
        print("✅ 已连接")
        print(f"监听 {duration} 秒...\n")
        
        await asyncio.sleep(duration)
        
        await browser.close()
    
    return messages


def decode_message(data: bytes):
    """解码二进制消息"""
    try:
        text = data.decode('utf-8', errors='ignore')
        
        # 查找 JSON
        json_start = text.find('{')
        if json_start < 0:
            return None
        
        json_text = text[json_start:]
        
        # 找匹配的 }
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
            if data.get("event") == "flash-hot-changed":
                for item in data.get("data", []):
                    content = item.get("data", {}).get("content", "")
                    if content:
                        print(f"🔥 {content[:100]}")
            elif data.get("event") == "flash":
                content = data.get("data", {}).get("content", "")
                if content:
                    print(f"📰 {content[:100]}")
            elif "content" in data:
                print(f"📰 {data['content'][:100]}")
    except:
        pass


def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    print(f"=== 金十快讯抓取器 ===\n")
    
    messages = asyncio.run(capture_jin10_flash(duration))
    
    print(f"\n共捕获 {len(messages)} 条消息")
    
    if messages:
        filename = f"jin10_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        print(f"已保存到 {filename}")


if __name__ == "__main__":
    main()