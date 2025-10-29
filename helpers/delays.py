import asyncio
import random

async def human_delays(min_ms: int = 500, max_ms: int = 1500):
    await asyncio.sleep(random.uniform(min_ms/1000, max_ms/1000))

async def human_typing(page, text:str, min_delay: int = 50, max_delay: int = 150):
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(min_delay/1000, max_delay/1000))