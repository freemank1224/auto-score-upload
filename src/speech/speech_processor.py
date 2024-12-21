import re
from dataclasses import dataclass

@dataclass
class GradeEntry:
    student_id: str
    grade: int

class SpeechProcessor:
    def __init__(self):
        # 匹配四位数字和成绩的正则表达式
        self.pattern = r'(\d{4})[^\d]*(\d{1,3})'
    
    def process_text(self, text: str) -> list[GradeEntry]:
        """处理语音识别文本，提取学号和成绩"""
        entries = []
        matches = re.finditer(self.pattern, text)
        
        for match in matches:
            student_id = match.group(1)
            grade = int(match.group(2))
            
            if 0 <= grade <= 100:  # 验证成绩是否在有效范围内
                entries.append(GradeEntry(student_id, grade))
                
        return entries 