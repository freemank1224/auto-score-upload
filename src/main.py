import asyncio
from src.speech.speech_recognizer import SenseVoiceRecognizer
from src.speech.speech_processor import SpeechProcessor
from src.utils.excel_processor import ExcelProcessor
import sounddevice as sd
import numpy as np

class GradeFillingSystem:
    def __init__(self):
        # 初始化将要使用的组件，在初始化阶段将其实例化
        self.recognizer = SenseVoiceRecognizer()    # 语音识别器
        self.processor = SpeechProcessor()          # 语音处理器
        self.excel_processor = ExcelProcessor()     # Excel处理器
        self.audio_device = self._select_audio_device()  # 选择录音设备
        
    def _select_audio_device(self):
        """选择录音设备"""
        print("\n可用的录音设备:")
        devices = sd.query_devices()
        input_devices = []
        seen_names = set()  # 用于跟踪已经显示的设备名称
        
        for i, device in enumerate(devices):
            # 只显示输入设备且不重复显示相同名称的设备
            if device['max_input_channels'] > 0:
                name = device['name']
                # 跳过已经显示过的设备名称
                if name in seen_names:
                    continue
                seen_names.add(name)
                print(f"{len(input_devices)}: {name}")
                input_devices.append(i)
        
        while True:
            try:
                choice = input("\n请选择录音设备编号 (输入数字): ")
                device_idx = input_devices[int(choice)]
                
                # 测试选择的设备
                print(f"请说话以测试设备...")
                
                # 设置默认设备
                sd.default.device = device_idx
                
                # 进行短时间测试录音
                duration = 2  # 1秒测试
                sample_rate = 16000
                test_data = sd.rec(
                    int(duration * sample_rate),
                    samplerate=sample_rate,
                    channels=1,
                    dtype='float32',
                    device=device_idx
                )
                sd.wait()
                
                # 检查录音是否成功
                if test_data is None or len(test_data) == 0:
                    raise Exception("测试录音失败")
                
                # 检查音量
                volume = np.sqrt(np.mean(test_data**2))
                if volume < 0.001:
                    print("警告: 未检测到音频输入，请检查麦克风是否静音")
                    if not input("是否继续使用此设备？(y/n): ").lower().startswith('y'):
                        continue
                
                print(f"已选择并测试设备: {devices[device_idx]['name']}")
                return device_idx
                
            except (ValueError, IndexError):
                print("无效的选择，请重试")
            except sd.PortAudioError as e:
                print(f"设备测试失败: {e}")
                print("请选择其他设备")
            except Exception as e:
                print(f"设备测试出错: {e}")
                print("请选择其他设备")
    
    async def start(self):
        """启动系统"""
        await self.speech_recognition_task()
    
    async def speech_recognition_task(self):
        """语音识别任务"""
        print("\n开始语音识别，说『结束』停止录音...")
        while True:
            audio_stream = await self.get_audio_stream()
            text = await self.recognizer.recognize(audio_stream)
            
            if text == "STOP_AND_PROCESS":
                # 处理最终结果
                result_dict = await self.recognizer.process_final_results()
                if result_dict:
                    print("\n是否更新Excel文件？(y/n): ")
                    if input().lower().startswith('y'):
                        self.excel_processor.process_grades()
                break
            elif text == "STOP":
                break

    async def get_audio_stream(self):
        """实时录音实现，增加错误处理和重试机制"""
        MAX_RETRIES = 3
        retry_count = 0
        SAMPLE_RATE = 16000  # 统一使用16kHz采样率
        
        while retry_count < MAX_RETRIES:
            try:
                duration = 6
                print(f"\n开始录音...（第 {retry_count + 1} 次尝试）")
                print("请开始说话...")
                
                # 录音
                audio_data = sd.rec(
                    int(duration * SAMPLE_RATE), 
                    samplerate=SAMPLE_RATE,
                    channels=1, 
                    dtype=np.float32,
                    device=self.audio_device
                )
                
                try:
                    await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, sd.wait),
                        timeout=duration + 2
                    )
                except asyncio.TimeoutError:
                    print("录音等待超时，正在重试...")
                    retry_count += 1
                    continue
                    
                # 确保音频数据是二维的 [1, audio_length]
                if len(audio_data.shape) == 1:
                    audio_data = audio_data.reshape(1, -1)
                
                # 音量检查
                volume_rms = np.sqrt(np.mean(audio_data**2))
                print(f"原始音量: {volume_rms:.6f}")
                
                if volume_rms < 0.001:
                    print("警告: 音量太小，正在重试...")
                    retry_count += 1
                    continue
                
                # 归一化音频数据
                max_abs = np.max(np.abs(audio_data))
                if max_abs > 0:
                    audio_data = audio_data / max_abs
                
                print(f"音频形状: {audio_data.shape}")
                print(f"采样率: {SAMPLE_RATE}")
                print("录音结束")
                return audio_data
                
            except Exception as e:
                print(f"录音出错: {e}")
                retry_count += 1
                if retry_count < MAX_RETRIES:
                    await asyncio.sleep(1)
        
        # 返回正确采样率的静音数据
        return np.zeros((1, 6 * SAMPLE_RATE), dtype=np.float32)

async def main():
    system = GradeFillingSystem()
    await system.start()

if __name__ == "__main__":
    asyncio.run(main()) 