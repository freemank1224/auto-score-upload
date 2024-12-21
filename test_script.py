import asyncio
from src.main import GradeFillingSystem
import os
import selenium.common.exceptions

async def test():
    # 获取当前目录的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建测试页面的URL
    test_page_path = os.path.join(current_dir, 'test_page.html')
    # test_page_url = f'file:///{test_page_path}'
    test_page_url = "http://jwgl.ujn.edu.cn/jwglxt/cjlrgl/jscjlr_cxJscjlrIndex.html?doType=details&gnmkdm=N302505&layout=default&su=000011703590"

    system = GradeFillingSystem()
    try:
        # Add a login step before accessing the grade page
        await system.start(test_page_url)
    except selenium.common.exceptions.TimeoutException as e:
        print("页面加载超时，可能原因：")
        print("1. 需要先登录")
        print("2. 网络连接问题")
        print("3. 页面结构已更改")
        await system.table_filler.close()
    except KeyboardInterrupt:
        print("测试结束")
        await system.table_filler.close()

if __name__ == "__main__":
    asyncio.run(test()) 