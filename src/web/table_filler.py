from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import asyncio
import os
from pathlib import Path

class TableFiller:
    def __init__(self):
        self.driver = None
        
    async def init(self):
        """初始化浏览器"""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')  # 无头模式
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--ignore-certificate-errors')  # 忽略证书错误
            options.add_argument('--ignore-ssl-errors')  # 忽略SSL错误
            
            # 尝试多种方式初始化driver
            try:
                # 方式1: 使用环境变量中的chromedriver
                self.driver = webdriver.Chrome(options=options)
            except Exception as e1:
                print(f"方式1失败: {e1}")
                try:
                    # 方式2: 在当前目录查找chromedriver
                    driver_path = Path('./chromedriver.exe')  # Windows
                    if not driver_path.exists():
                        driver_path = Path('./chromedriver')  # Linux/Mac
                    
                    if driver_path.exists():
                        service = Service(str(driver_path))
                        self.driver = webdriver.Chrome(service=service, options=options)
                    else:
                        raise Exception("找不到chromedriver")
                except Exception as e2:
                    print(f"方式2失败: {e2}")
                    # 方式3: 使用selenium-manager自动管理
                    self.driver = webdriver.Chrome(options=options)
            
            print("成功初始化浏览器")
            
        except Exception as e:
            print(f"初始化浏览器失败: {e}")
            raise
        
    async def fill_grade(self, cell_selector: str, grade: int):
        """填充成绩到指定单元格"""
        try:
            # 等待元素可见
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, cell_selector))
            )
            # 清除原有内容
            element.clear()
            # 填入新成绩
            element.send_keys(str(grade))
            # 等待一小段时间确保填写完成
            print(f"正在填写成绩: {grade} 到位置: {cell_selector}")
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f"填写成绩失败: {e}")
            
    async def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()