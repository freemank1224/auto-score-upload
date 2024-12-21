import asyncio
from collections import deque

class DataQueue:
    def __init__(self):
        self.queue = deque()
        self.lock = asyncio.Lock()
        self.event = asyncio.Event()
    
    async def put(self, item):
        """添加数据到队列"""
        async with self.lock:
            self.queue.append(item)
            self.event.set()
    
    async def get(self):
        """从队列获取数据"""
        await self.event.wait()
        async with self.lock:
            if not self.queue:
                self.event.clear()
                return None
            return self.queue.popleft() 