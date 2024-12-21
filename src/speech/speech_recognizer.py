from abc import ABC, abstractmethod
import azure.cognitiveservices.speech as speechsdk
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess
import numpy as np
import torch

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
    
    async def recognize(self, audio_stream):
        """
        使用SenseVoice进行语音识别，增加错误处理
        """
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