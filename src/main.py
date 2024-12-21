import asyncio
from src.speech.speech_recognizer import SenseVoiceRecognizer
from src.speech.speech_processor import SpeechProcessor
from src.web.page_analyzer import WebPageAnalyzer
from src.web.table_filler import TableFiller
from src.utils.data_queue import DataQueue
import sounddevice as sd
import numpy as np

class GradeFillingSystem:
    def __init__(self):
        self.recognizer = SenseVoiceRecognizer()
        self.processor = SpeechProcessor()
        self.web_analyzer = WebPageAnalyzer()
        self.table_filler = TableFiller()
        self.data_queue = DataQueue()
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
                print(f"正在测试设备...")
                
                # 设置默认设备
                sd.default.device = device_idx
                
                # 进行短时间测试录音
                duration = 1  # 1秒测试
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
    
    async def start(self, webpage_url: str):
        """启动系统"""
        await self.table_filler.init()
        
        # 启动并行任务
        await asyncio.gather(
            self.speech_recognition_task(),
            self.table_filling_task(webpage_url)
        )
    
    async def speech_recognition_task(self):
        """语音识别任务"""
        while True:
            audio_stream = await self.get_audio_stream()
            text = await self.recognizer.recognize(audio_stream)
            
            if text == "STOP_AND_PROCESS":
                # 处理最终结果
                result_dict = await self.recognizer.process_final_results()
                if result_dict:
                    # 将结果添加到队列中
                    for student_id, grade in result_dict.items():
                        entry = self.processor.create_entry(student_id, grade)
                        if entry:
                            await self.data_queue.put(entry)
                break
            elif text == "STOP":
                break
            else:
                entries = self.processor.process_text(text)
                for entry in entries:
                    await self.data_queue.put(entry)
    
    async def table_filling_task(self, webpage_url: str):
        """表格填充任务"""
        self.table_filler.driver.get(webpage_url)
        table_structure = await self.web_analyzer.analyze_table(
            self.table_filler.driver
        )
        
        while True:
            entry = await self.data_queue.get()
            if entry is None:
                continue
                
            # 查找匹配的学号并填充成绩
            found = False
            for row in table_structure['rows']:
                # 获取完整学号的后四位进行匹配
                full_student_id = row['student_id']
                last_four_digits = full_student_id[-4:]
                
                if entry.student_id == last_four_digits:
                    try:
                        # 确保所有值都转换为字符串
                        row_index = str(row['row_element'].get_attribute('rowIndex'))
                        grade_col = str(table_structure['grade_col'] + 1)
                        cell_selector = f"tr:nth-child({row_index}) td:nth-child({grade_col})"
                        await self.table_filler.fill_grade(cell_selector, entry.grade)
                        print(f"已填写: 完整学号 {full_student_id} (后四位: {last_four_digits}) 的成绩 {entry.grade}")
                        found = True
                        break
                    except Exception as e:
                        print(f"填写成绩时出错: {e}")
                        continue
            
            if not found:
                print(f"警告: 未找到匹配的学号 {entry.student_id}")

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
    await system.start("http://jwgl.ujn.edu.cn/jwglxt/cjlrgl/jscjlr_cxJscjlrIndex.html?doType=details&gnmkdm=N302505&layout=default&su=000011703590")

if __name__ == "__main__":
    asyncio.run(main()) 