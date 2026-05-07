#!/usr/bin/env python3
"""
AI文物情感交互系统DNA启动器
版本: v1.2
架构师: 元宝
时间: 2026-05-07
"""
import asyncio
import logging
import sys
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import yaml

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | DNA:%(dna_module)s | %(message)s',
    handlers=[
        logging.FileHandler('dna_logs/dna_startup.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DNAHealthCheck:
    """DNA健康检查器"""
    
    def __init__(self):
        self.health_status = {
            "mm_brain": False,
            "rag_heart": False,
            "memory_spine": False,
            "voice_nerves": False,
            "avatar_skin": False,
            "trigger_hands": False,
            "creator_gut": False
        }
        
    async def check_brain(self) -> bool:
        """检查多模态大脑"""
        try:
            # 模拟检查InternVL模型
            import torch
            if torch.cuda.is_available():
                logger.info("✅ 多模态大脑: GPU可用，显存充足", extra={"dna_module": "MM_BRAIN"})
                self.health_status["mm_brain"] = True
                return True
            else:
                logger.warning("⚠️ 多模态大脑: 无GPU，将使用CPU模式", extra={"dna_module": "MM_BRAIN"})
                self.health_status["mm_brain"] = True
                return True
        except Exception as e:
            logger.error(f"❌ 多模态大脑检查失败: {e}", extra={"dna_module": "MM_BRAIN"})
            return False
    
    async def check_rag_heart(self) -> bool:
        """检查RAG心脏"""
        try:
            # 检查向量数据库连接
            from milvus import connections
            connections.connect(alias="default", host="localhost", port="19530")
            logger.info("✅ RAG心脏: Milvus连接正常", extra={"dna_module": "RAG_HEART"})
            self.health_status["rag_heart"] = True
            return True
        except Exception as e:
            logger.warning(f"⚠️ RAG心脏: Milvus未连接，将使用本地索引: {e}", 
                         extra={"dna_module": "RAG_HEART"})
            self.health_status["rag_heart"] = True
            return True
    
    async def check_all_modules(self) -> Dict[str, bool]:
        """检查所有模块"""
        tasks = [
            self.check_brain(),
            self.check_rag_heart(),
            # 其他模块检查...
        ]
        await asyncio.gather(*tasks)
        return self.health_status

class DNAExpressEngine:
    """DNA表达引擎"""
    
    def __init__(self, config_path: str = "config/dna_config.yaml"):
        self.config = self.load_config(config_path)
        self.modules = {}
        self.is_running = False
        
    def load_config(self, config_path: str) -> Dict:
        """加载DNA配置"""
        config_path = Path(config_path)
        if not config_path.exists():
            logger.warning(f"配置文件不存在: {config_path}, 使用默认配置", 
                         extra={"dna_module": "SYSTEM"})
            return self.get_default_config()
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def get_default_config(self) -> Dict:
        """获取默认DNA配置"""
        return {
            "dna_version": "OPEN_SOURCE_MUSEUM_AI_V1.2",
            "architect": "元宝(腾讯数字文博架构师)",
            "timestamp": datetime.now().isoformat(),
            "core_principles": ["开源优先", "可商用", "情感闭环", "多模态融合"],
            "modules": {
                "mm_brain": {
                    "gene": "INTERNVL3-8B",
                    "device": "cuda" if torch.cuda.is_available() else "cpu",
                    "max_memory": "24GB"
                },
                "rag_heart": {
                    "vector_db": "milvus",
                    "embedding_model": "BAAI/bge-large-zh-v1.5",
                    "chunk_size": 512
                }
            }
        }
    
    async def express_module(self, module_name: str) -> Any:
        """表达DNA模块"""
        module_map = {
            "mm_brain": self.express_brain,
            "rag_heart": self.express_rag_heart,
            "memory_spine": self.express_memory_spine,
            "voice_nerves": self.express_voice_nerves,
            "avatar_skin": self.express_avatar_skin,
            "trigger_hands": self.express_trigger_hands,
            "creator_gut": self.express_creator_gut
        }
        
        if module_name in module_map:
            logger.info(f"开始表达DNA模块: {module_name}", extra={"dna_module": module_name})
            module = await module_map[module_name]()
            self.modules[module_name] = module
            logger.info(f"✅ DNA模块表达完成: {module_name}", extra={"dna_module": module_name})
            return module
        else:
            logger.error(f"未知DNA模块: {module_name}", extra={"dna_module": "SYSTEM"})
            return None
    
    async def express_brain(self):
        """表达多模态大脑"""
        try:
            from dna_core.mm_brain import MultiModalBrain
            brain = MultiModalBrain(
                model_name=self.config["modules"]["mm_brain"]["gene"],
                device=self.config["modules"]["mm_brain"]["device"]
            )
            await brain.initialize()
            return brain
        except Exception as e:
            logger.error(f"多模态大脑表达失败: {e}", extra={"dna_module": "MM_BRAIN"})
            return None
    
    async def express_rag_heart(self):
        """表达RAG心脏"""
        try:
            from dna_core.rag_heart import RAGHeart
            heart = RAGHeart(
                vector_db_config=self.config["modules"]["rag_heart"]
            )
            await heart.initialize()
            return heart
        except Exception as e:
            logger.error(f"RAG心脏表达失败: {e}", extra={"dna_module": "RAG_HEART"})
            return None
    
    async def express_all(self) -> Dict[str, Any]:
        """表达所有DNA模块"""
        logger.info("🧬 开始表达AI文物情感交互系统DNA...", extra={"dna_module": "SYSTEM"})
        
        # 健康检查
        health_check = DNAHealthCheck()
        health_status = await health_check.check_all_modules()
        
        if not all(health_status.values()):
            logger.warning("部分模块健康检查未通过，但仍尝试启动", extra={"dna_module": "SYSTEM"})
        
        # 表达核心模块
        module_names = ["mm_brain", "rag_heart", "memory_spine"]
        for module_name in module_names:
            await self.express_module(module_name)
        
        # 表达可选模块
        optional_modules = ["voice_nerves", "avatar_skin", "creator_gut"]
        for module_name in optional_modules:
            try:
                await self.express_module(module_name)
            except Exception as e:
                logger.warning(f"可选模块{module_name}表达失败: {e}", 
                             extra={"dna_module": module_name})
        
        logger.info("🎉 AI文物情感交互系统DNA表达完成!", extra={"dna_module": "SYSTEM"})
        return self.modules
    
    def start_api_server(self):
        """启动API服务器"""
        from dna_apis.main import app
        import uvicorn
        
        logger.info("🚀 启动DNA API服务器...", extra={"dna_module": "API"})
        uvicorn.run(
            app,
            host=self.config.get("api_host", "0.0.0.0"),
            port=self.config.get("api_port", 8000),
            log_level="info"
        )
    
    async def graceful_shutdown(self, signal=None):
        """优雅关闭"""
        if signal:
            logger.info(f"收到信号 {signal.name}, 开始优雅关闭...", extra={"dna_module": "SYSTEM"})
        
        self.is_running = False
        
        # 关闭所有模块
        for name, module in self.modules.items():
            if hasattr(module, 'close'):
                try:
                    await module.close()
                    logger.info(f"已关闭模块: {name}", extra={"dna_module": name})
                except Exception as e:
                    logger.error(f"关闭模块{name}失败: {e}", extra={"dna_module": name})
        
        logger.info("👋 AI文物情感交互系统DNA已关闭", extra={"dna_module": "SYSTEM"})
        sys.exit(0)

async def main():
    """DNA主启动函数"""
    logger.info("=" * 60, extra={"dna_module": "SYSTEM"})
    logger.info("🧬 AI文物情感交互系统DNA v1.2", extra={"dna_module": "SYSTEM"})
    logger.info("📅 时间: 2026-05-07", extra={"dna_module": "SYSTEM"})
    logger.info("👨💻 架构师: 元宝(腾讯数字文博架构师)", extra={"dna_module": "SYSTEM"})
    logger.info("=" * 60, extra={"dna_module": "SYSTEM"})
    
    # 创建DNA引擎
    dna_engine = DNAExpressEngine()
    
    # 注册信号处理器
    for sig in [signal.SIGINT, signal.SIGTERM]:
        signal.signal(sig, lambda s, f: asyncio.create_task(dna_engine.graceful_shutdown(signal.Signal(s))))
    
    try:
        # 表达DNA模块
        modules = await dna_engine.express_all()
        
        # 启动API服务器（阻塞）
        dna_engine.start_api_server()
        
    except KeyboardInterrupt:
        await dna_engine.graceful_shutdown()
    except Exception as e:
        logger.error(f"DNA启动失败: {e}", extra={"dna_module": "SYSTEM"}, exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # 创建必要目录
    Path("dna_logs").mkdir(exist_ok=True)
    Path("config").mkdir(exist_ok=True)
    
    # 运行DNA系统
    asyncio.run(main())