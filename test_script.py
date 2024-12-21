import asyncio
from src.main import GradeFillingSystem
import os

async def test():
    # 获取当前目录的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建测试页面的URL
    test_page_path = os.path.join(current_dir, 'test_page.html')
    test_page_url = f'file:///{test_page_path}'
    
    system = GradeFillingSystem()
    try:
        await system.start(test_page_url)
    except KeyboardInterrupt:
        print("测试结束")
        await system.table_filler.close()

if __name__ == "__main__":
    asyncio.run(test()) 