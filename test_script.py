import asyncio
from src.main import GradeFillingSystem

async def test():
    system = GradeFillingSystem()
    try:
        await system.start()
    except KeyboardInterrupt:
        print("\n程序已终止")

if __name__ == "__main__":
    asyncio.run(test()) 