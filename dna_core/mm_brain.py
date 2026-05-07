"""
多模态大脑模块
基因: INTERNVL3-8B
功能: 视觉理解、图文对话、复杂推理
"""
import torch
import asyncio
from typing import Dict, List, Any, Optional, Union
from PIL import Image
import logging
from dataclasses import dataclass
from transformers import AutoModel, AutoTokenizer, AutoProcessor
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class BrainConfig:
    """大脑配置"""
    model_name: str = "OpenGVLab/InternVL3-8B"
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    dtype: torch.dtype = torch.float16
    max_length: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    use_cache: bool = True

class MultiModalBrain:
    """多模态大脑实现"""
    
    def __init__(self, config: Optional[BrainConfig] = None):
        self.config = config or BrainConfig()
        self.model = None
        self.tokenizer = None
        self.processor = None
        self.is_initialized = False
        
    async def initialize(self):
        """初始化模型"""
        try:
            logger.info(f"正在加载多模态大脑模型: {self.config.model_name}", 
                       extra={"dna_module": "MM_BRAIN"})
            
            # 加载tokenizer和processor
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_name,
                trust_remote_code=True
            )
            self.processor = AutoProcessor.from_pretrained(
                self.config.model_name,
                trust_remote_code=True
            )
            
            # 加载模型
            self.model = AutoModel.from_pretrained(
                self.config.model_name,
                torch_dtype=self.config.dtype,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            ).to(self.config.device).eval()
            
            self.is_initialized = True
            logger.info(f"✅ 多模态大脑加载完成，设备: {self.config.device}", 
                       extra={"dna_module": "MM_BRAIN"})
            
        except Exception as e:
            logger.error(f"❌ 多模态大脑初始化失败: {e}", 
                        extra={"dna_module": "MM_BRAIN"}, exc_info=True)
            raise
    
    async def process_text(self, 
                          text: str, 
                          context: Optional[str] = None) -> Dict[str, Any]:
        """处理文本输入"""
        if not self.is_initialized:
            raise RuntimeError("多模态大脑未初始化")
        
        try:
            # 构建输入
            messages = []
            if context:
                messages.append({"role": "system", "content": context})
            messages.append({"role": "user", "content": text})
            
            # 生成响应
            with torch.no_grad():
                inputs = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=True,
                    add_generation_prompt=True,
                    return_tensors="pt"
                ).to(self.config.device)
                
                outputs = self.model.generate(
                    inputs,
                    max_length=self.config.max_length,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    do_sample=True,
                    use_cache=self.config.use_cache
                )
                
                response = self.tokenizer.decode(
                    outputs[0][inputs.shape[1]:], 
                    skip_special_tokens=True
                )
            
            return {
                "text": response,
                "tokens": len(outputs[0]),
                "thinking_time": 0.0,  # 实际计算推理时间
                "success": True
            }
            
        except Exception as e:
            logger.error(f"文本处理失败: {e}", extra={"dna_module": "MM_BRAIN"})
            return {
                "text": "抱歉，我暂时无法处理这个问题。",
                "error": str(e),
                "success": False
            }
    
    async def process_image_text(self, 
                               image: Union[Image.Image, str, np.ndarray],
                               text: str,
                               context: Optional[str] = None) -> Dict[str, Any]:
        """处理图像+文本输入"""
        if not self.is_initialized:
            raise RuntimeError("多模态大脑未初始化")
        
        try:
            # 预处理图像
            if isinstance(image, str):
                image = Image.open(image).convert("RGB")
            
            # 准备多模态输入
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": text}
                    ]
                }
            ]
            
            if context:
                messages.insert(0, {"role": "system", "content": context})
            
            # 生成响应
            with torch.no_grad():
                inputs = self.processor(
                    messages,
                    self.tokenizer,
                    padding=True,
                    return_tensors="pt"
                ).to(self.config.device)
                
                outputs = self.model.generate(
                    **inputs,
                    max_length=self.config.max_length,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    do_sample=True
                )
                
                response = self.tokenizer.decode(
                    outputs[0][inputs["input_ids"].shape[1]:], 
                    skip_special_tokens=True
                )
            
            return {
                "text": response,
                "has_image": True,
                "image_understood": True,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"图文处理失败: {e}", extra={"dna_module": "MM_BRAIN"})
            return {
                "text": "抱歉，我暂时无法分析这张图片。",
                "error": str(e),
                "success": False
            }
    
    async def analyze_artifact(self, 
                             image: Image.Image,
                             artifact_info: Dict[str, Any]) -> Dict[str, Any]:
        """分析文物"""
        prompt = f"""
        请分析这个文物：
        名称：{artifact_info.get('name', '未知')}
        年代：{artifact_info.get('era', '未知')}
        材质：{artifact_info.get('material', '未知')}
        
        请从以下角度分析：
        1. 视觉特征描述
        2. 历史背景推测
        3. 文化意义
        4. 可能的用途
        5. 保存状况评估
        """
        
        result = await self.process_image_text(image, prompt)
        
        # 提取关键信息
        analysis = {
            "description": result["text"],
            "characteristics": self._extract_characteristics(result["text"]),
            "historical_context": self._extract_historical_context(result["text"]),
            "cultural_significance": self._extract_cultural_significance(result["text"]),
            "preservation_status": self._extract_preservation_status(result["text"])
        }
        
        return analysis
    
    def _extract_characteristics(self, text: str) -> List[str]:
        """提取特征"""
        # 简化实现，实际应该用NER或信息提取模型
        characteristics = []
        keywords = ["纹饰", "造型", "工艺", "色彩", "图案", "铭文", "款识"]
        for kw in keywords:
            if kw in text:
                characteristics.append(kw)
        return characteristics
    
    def _extract_historical_context(self, text: str) -> str:
        """提取历史背景"""
        # 简化实现
        if "商" in text or "周" in text:
            return "商周时期"
        elif "唐" in text or "宋" in text:
            return "唐宋时期"
        elif "明" in text or "清" in text:
            return "明清时期"
        return "古代"
    
    def _extract_cultural_significance(self, text: str) -> str:
        """提取文化意义"""
        if "礼器" in text:
            return "礼制象征"
        elif "实用" in text or "生活" in text:
            return "日常生活"
        elif "宗教" in text or "信仰" in text:
            return "宗教信仰"
        return "文化传承"
    
    def _extract_preservation_status(self, text: str) -> str:
        """提取保存状况"""
        if "完整" in text or "完好" in text:
            return "良好"
        elif "破损" in text or "残缺" in text:
            return "一般"
        elif "严重" in text or "损毁" in text:
            return "较差"
        return "未知"
    
    async def close(self):
        """关闭模型，释放资源"""
        if self.model:
            del self.model
            torch.cuda.empty_cache()
        self.is_initialized = False
        logger.info("多模态大脑已关闭", extra={"dna_module": "MM_BRAIN"")

class SelfCheckMixin:
    """自检机制混入类"""
    
    async def self_check(self) -> Dict[str, Any]:
        """执行自检"""
        checks = {}
        
        # 检查模型是否加载
        checks["model_loaded"] = self.model is not None
        checks["tokenizer_loaded"] = self.tokenizer is not None
        checks["processor_loaded"] = self.processor is not None
        
        # 检查GPU内存
        if torch.cuda.is_available():
            gpu_memory = torch.cuda.memory_allocated() / 1024**3
            checks["gpu_memory_gb"] = round(gpu_memory, 2)
            checks["gpu_available"] = True
        else:
            checks["gpu_available"] = False
        
        # 简单推理测试
        try:
            test_result = await self.process_text("你好")
            checks["inference_works"] = test_result["success"]
            checks["response_time"] = 0.1  # 占位符
        except Exception as e:
            checks["inference_works"] = False
            checks["inference_error"] = str(e)
        
        return {
            "module": "mm_brain",
            "status": all(checks.values()),
            "checks": checks,
            "timestamp": asyncio.get_event_loop().time()
        }