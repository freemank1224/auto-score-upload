from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import cv2
import numpy as np
from PIL import Image
import io
import os
import requests
from pathlib import Path
from tqdm import tqdm

class WebPageAnalyzer:
    def __init__(self):
        # 创建权重目录
        self.weights_dir = Path('weights/icon_detect_v1_5')
        self.weights_dir.mkdir(parents=True, exist_ok=True)
        
        # 模型文件路径
        self.model_path = self.weights_dir / 'model_v1_5.pt'
        
        # 如果模型文件不存在，则下载
        if not self.model_path.exists():
            self._download_model()
            
        # 现在可以安全地加载模型
        from transformers import AutoProcessor, AutoModelForVision2Seq
        from ultralytics import YOLO
        
        self.icon_detect_model = YOLO(str(self.model_path))
        print("成功加载目标检测模型")
        
        # 暂时不使用caption模型，简化实现
        # self.caption_model_name = "microsoft/OmniParser"
        # self.processor = AutoProcessor.from_pretrained(self.caption_model_name)
        # self.model = AutoModelForVision2Seq.from_pretrained(self.caption_model_name)
        
    def _download_model(self):
        """下载模型文件"""
        print("正在下载模型文件...")
        url = "https://huggingface.co/microsoft/OmniParser/resolve/main/icon_detect_v1_5/model_v1_5.pt"
        
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        with open(self.model_path, 'wb') as file, tqdm(
            desc=self.model_path.name,
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as pbar:
            for data in response.iter_content(chunk_size=1024):
                size = file.write(data)
                pbar.update(size)
        print("模型下载完成")
        
    async def analyze_table(self, driver):
        """分析网页表格结构"""
        # 等待表格加载完成
        table = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        
        # 直接使用Selenium的方式查找表格元素
        headers = driver.find_elements(By.TAG_NAME, "th")
        student_id_col = -1
        grade_col = -1
        
        # 查找列索引
        for idx, header in enumerate(headers):
            header_text = header.text.lower()
            if "学号" in header_text:
                student_id_col = idx
            elif "期末" in header_text:
                grade_col = idx
                
        # 获取所有行
        rows = []
        table_rows = driver.find_elements(By.TAG_NAME, "tr")[1:]  # 跳过表头行
        
        for row in table_rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) > student_id_col:
                student_id = cells[student_id_col].text
                if student_id.isdigit():
                    rows.append({
                        'student_id': student_id,
                        'row_element': row
                    })
        
        print(f"找到 {len(rows)} 行数据")
        print(f"学号列索引: {student_id_col}, 成绩列索引: {grade_col}")
        
        return {
            'student_id_col': student_id_col,
            'grade_col': grade_col,
            'rows': rows
        }
    
    def _find_column_index(self, elements, column_name):
        """查找指定列名的索引"""
        for idx, element in enumerate(elements):
            if column_name.lower() in element['description'].lower():
                return idx
        return -1