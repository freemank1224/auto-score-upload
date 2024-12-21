import pandas as pd
import json
import os
from openpyxl import load_workbook

class ExcelProcessor:
    def __init__(self, excel_path="test_table.xlsx"):
        self.excel_path = excel_path
        self.output_path = "updated_" + os.path.basename(self.excel_path)
        
    def process_grades(self, json_path="recognition_results.json"):
        """根据JSON文件更新Excel中的成绩"""
        try:
            # 首先检查是否存在更新后的文件
            if os.path.exists(self.output_path):
                print(f"\n读取现有的更新文件: {self.output_path}")
                df = pd.read_excel(
                    self.output_path,
                    dtype={'学号': str}
                )
                print("成功读取现有更新文件")
            else:
                # 如果不存在，则读取原始文件
                print(f"\n读取原始Excel文件: {self.excel_path}")
                df = pd.read_excel(
                    self.excel_path,
                    dtype={'学号': str}
                )
                print("成功读取原始文件")
            
            # 读取JSON文件
            print(f"读取JSON文件: {json_path}")
            with open(json_path, 'r', encoding='utf-8') as f:
                grades_dict = json.load(f)
            
            print(f"\n开始处理成绩数据...")
            print(f"JSON文件中包含 {len(grades_dict)} 条成绩记录")
            
            # 记录匹配情况
            matched_count = 0
            updated_count = 0
            unmatched = []
            
            # 遍历DataFrame的每一行
            for index, row in df.iterrows():
                student_id = str(row['学号'])  # 确保学号为字符串类型
                last_four = student_id[-4:]  # 获取学号后四位
                
                # 检查是否在成绩字典中
                if last_four in grades_dict:
                    current_grade = row.get('期末(必填)', None)
                    new_grade = float(grades_dict[last_four])
                    
                    if pd.isna(current_grade):
                        # 如果当前没有成绩，直接添加
                        df.at[index, '期末(必填)'] = new_grade
                        matched_count += 1
                        print(f"新增成绩: 学�� {student_id} (后四位: {last_four}) -> 成绩 {new_grade}")
                    else:
                        # 如果已有成绩，显示更新信息
                        df.at[index, '期末(必填)'] = new_grade
                        updated_count += 1
                        print(f"更新成绩: 学号 {student_id} (后四位: {last_four}) {current_grade} -> {new_grade}")
                else:
                    unmatched.append(last_four)
            
            # 打印统计信息
            print("\n处理完成!")
            print(f"总记录数: {len(df)}")
            print(f"新增成绩: {matched_count}")
            print(f"更新成绩: {updated_count}")
            print(f"未匹配: {len(unmatched)}")
            
            if unmatched:
                print("\n未匹配的学号后四位:")
                for sid in unmatched:
                    print(f"- {sid}")
            
            # 保存更新后的Excel文件，确保学号列作为文本保存
            with pd.ExcelWriter(
                self.output_path,
                engine='openpyxl',
                mode='w'
            ) as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')
                
                # 获取工作表
                worksheet = writer.sheets['Sheet1']
                
                # 找到学号列的索引
                student_id_col = None
                for idx, col in enumerate(df.columns):
                    if col == '学号':
                        student_id_col = idx + 1
                        break
                
                # 设置学号列的格式为文本
                if student_id_col:
                    for row in range(2, len(df) + 2):
                        cell = worksheet.cell(row=row, column=student_id_col)
                        cell.number_format = '@'
            
            print(f"\n更新后的文件已保存为: {self.output_path}")
            print("学号列已设置为文本格式")
            
            return True
            
        except Exception as e:
            print(f"处理Excel文件时出错: {e}")
            import traceback
            print("错误堆栈:", traceback.format_exc())
            return False