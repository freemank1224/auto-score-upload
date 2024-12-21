from abc import ABC, abstractmethod
import azure.cognitiveservices.speech as speechsdk
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess
import numpy as np
import torch
import json
import requests

class SpeechRecognizer(ABC):
    @abstractmethod
    async def recognize(self, audio_stream):
        pass

class SenseVoiceRecognizer(SpeechRecognizer):
    def __init__(self, model_dir="iic/SenseVoiceSmall"):
        self.model = AutoModel(
            model=model_dir,
            trust_remote_code=True,
            vad_model="fsmn-vad",
            vad_kwargs={"max_single_segment_time": 30000},
            device="cuda:0" if torch.cuda.is_available() else "cpu"
        )
        self.recognition_results = []  # 存储所有识别结果
        self.ollama_url = "http://192.168.31.70:11434/"  # Ollama API地址
        
    def should_stop(self, text):
        """检查是否包含停止指令"""
        stop_words = ["结束", "完毕", "停止"]
        return any(word in text for word in stop_words)
    
    async def process_final_results(self):
        """处理最终的识别结果"""
        if not self.recognition_results:
            print("没有识别结果需要处理")
            return None
            
        # 首先打印所有识别结果
        print("\n所有识别结果:")
        print("-" * 50)
        for idx, result in enumerate(self.recognition_results, 1):
            print(f"{idx}. {result}")
        print("-" * 50)
        
        # 直接使用手动解析，不依赖LLM
        result_dict = self._manual_parse_results()
        if result_dict:
            # 打印统计信息
            print("\n成绩统计信息:")
            print("-" * 50)
            print(f"总共识别到 {len(result_dict)} 条有效成绩")
            print("详细信息:")
            for student_id, score in result_dict.items():
                print(f"学号后四位: {student_id}, 分数: {score}")
            print("-" * 50)
            
            # 将结果保存为JSON文件
            with open('recognition_results.json', 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, ensure_ascii=False, indent=2)
            print("\n结果已保存到 recognition_results.json")
            return result_dict
            
        print("手动解析失败，无有效结果")
        return None

    def _manual_parse_results(self):
        """手动解析识别结果"""
        try:
            result_dict = {}
            invalid_lines = []  # 记录无效的行
            
            for idx, text in enumerate(self.recognition_results, 1):
                # 使用正则表达式提取学号和分数
                import re
                # 匹配四位数字（学号）和分数
                matches = re.findall(r'(\d{4}).*?(?:得分|分数|成绩)[：:]*(\d+)', text)
                
                if not matches:
                    invalid_lines.append((idx, text, "未找到有效的学号和分数"))
                    continue
                
                valid_pair_found = False
                for student_id, score in matches:
                    # 验证学号和分数的有效性
                    if len(student_id) == 4 and student_id.isdigit():
                        try:
                            score_int = int(score)
                            if 0 <= score_int <= 100:  # 确保分数在有效范围内
                                result_dict[str(student_id)] = str(score_int)
                                valid_pair_found = True
                            else:
                                invalid_lines.append((idx, text, f"分数 {score_int} 超出有效范围(0-100)"))
                        except ValueError:
                            invalid_lines.append((idx, text, f"分数 {score} 不是有效数字"))
                    else:
                        invalid_lines.append((idx, text, f"学号 {student_id} 不是有效的四位数字"))
                
                if not valid_pair_found and (idx, text) not in [x[:2] for x in invalid_lines]:
                    invalid_lines.append((idx, text, "未找到有效的学号和分数对"))
            
            # 打印处理结果
            print("\n解析结果:")
            print("-" * 50)
            if result_dict:
                print("有效数据:")
                for student_id, score in result_dict.items():
                    print(f"学号: {student_id}, 分数: {score}")
            
            if invalid_lines:
                print("\n以下行被忽略:")
                for idx, text, reason in invalid_lines:
                    print(f"第 {idx} 行: {text}")
                    print(f"原因: {reason}")
            print("-" * 50)
            
            if result_dict:
                return result_dict
            else:
                print("没有找到任何有效的学号和分数对")
                return None
            
        except Exception as e:
            print(f"手动解析失败: {e}")
            import traceback
            print("错误堆栈:", traceback.format_exc())
            return None
    
    async def recognize(self, audio_stream):
        """使用SenseVoice进行语音识别，增加错误处理"""
        try:
            if audio_stream is None or audio_stream.size == 0:
                print("警告: 收到空音频流")
                return ""
            
            # 确保音频数据是一维的
            if len(audio_stream.shape) > 1:
                audio_stream = audio_stream.squeeze()  # 移除所有维度为1的维度
                if len(audio_stream.shape) > 1:  # 如果还是多维，则取平均
                    audio_stream = audio_stream.mean(axis=0)
            
            # 打印调试信息
            print(f"音频数据形状(numpy): {audio_stream.shape}")
            
            # 转换为PyTorch张量
            audio_tensor = torch.from_numpy(audio_stream).float()
            
            # 确保音频长度足够
            min_length = 16000  # 至少1秒
            if len(audio_tensor) < min_length:
                audio_tensor = torch.nn.functional.pad(
                    audio_tensor, 
                    (0, min_length - len(audio_tensor))
                )
            
            # 移动到正确的设备
            if torch.cuda.is_available():
                audio_tensor = audio_tensor.cuda()
            
            # 打印调试信息
            print(f"音频张量形状(torch): {audio_tensor.shape}")
            print(f"音频范围: [{audio_tensor.min():.3f}, {audio_tensor.max():.3f}]")
            print(f"音频设备: {audio_tensor.device}")
            print(f"音频维度: {audio_tensor.dim()}")
            
            # 调用模型
            res = self.model.generate(
                input=audio_tensor,  # 一维音频数据
                input_len=torch.tensor([len(audio_tensor)], device=audio_tensor.device),
                cache={},
                language="zh",
                use_itn=True,
                batch_size_s=60,
                merge_vad=True,
                merge_length_s=15,
            )
            
            if not res or len(res) == 0:
                print("警告: 识别结果为空")
                return ""
            
            text = rich_transcription_postprocess(res[0]["text"])
            print(f"识别结果: {text}")
            
            # 将结果添加到列表中
            if text.strip():  # 如果不是空字符串
                self.recognition_results.append(text)
            
            # 检查是否需要停止
            if self.should_stop(text):
                print("\n检测到停止指令")
                # 首先打印当前所有识别结果
                print("\n当前所有识别结果:")
                print("-" * 50)
                for idx, result in enumerate(self.recognition_results, 1):
                    print(f"{idx}. {result}")
                print("-" * 50)
                
                user_input = input("\n是否将语音结果整理为表格？(y/n): ")
                if user_input.lower().startswith('y'):
                    return "STOP_AND_PROCESS"
                else:
                    return "STOP"
            
            return text
            
        except Exception as e:
            print(f"语音识别出错: {e}")
            print(f"错误类型: {type(e)}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            return ""

class AzureSpeechRecognizer(SpeechRecognizer):
    def __init__(self, subscription_key, region):
        self.speech_config = speechsdk.SpeechConfig(
            subscription=subscription_key, 
            region=region
        )
        
    async def recognize(self, audio_stream):
        try:
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config
            )
            result = await speech_recognizer.recognize_once_async()
            return result.text if result.text else ""
        except Exception as e:
            print(f"Azure语音识别出错: {e}")
            return ""