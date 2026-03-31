"""
金十快讯转发器 - 只发送新消息
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# 已发送消息的ID记录
SENT_IDS_FILE = "/tmp/jin10_sent_ids.json"
sent_ids = set()

def load_sent_ids():
    global sent_ids
    if os.path.exists(SENT_IDS_FILE):
        try:
            with open(SENT_IDS_FILE, "r") as f:
                sent_ids = set(json.load(f))
        except:
            pass

def save_sent_ids():
    try:
        with open(SENT_IDS_FILE, "w") as f:
            json.dump(list(sent_ids)[-500:], f)
    except:
        pass

async def monitor():
    import httpx
    
    load_sent_ids()
    last_count = 0
    
    print("[监控] 启动，检查新消息...")
    
    while True:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get("http://localhost:19999/api/messages/latest?limit=20")
                data = resp.json()
                messages = data.get("messages", [])
                
                new_messages = []
                for msg in messages:
                    msg_data = msg.get("data", {})
                    msg_id = msg_data.get("id", "")
                    content = msg_data.get("content", "")
                    
                    if msg_id and msg_id not in sent_ids and content:
                        sent_ids.add(msg_id)
                        new_messages.append({
                            "time": msg_data.get("time", ""),
                            "content": content[:200]
                        })
                
                if new_messages:
                    save_sent_ids()
                    # 输出新消息（会被捕获）
                    for m in new_messages:
                        print(f"[新消息] {m['time']} | {m['content']}")
            
            await asyncio.sleep(10)
            
        except Exception as e:
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(monitor())
