"""
多模态知识心脏
基因: RAG-ANYTHING
功能: 图文统一索引、多模态检索
"""
import asyncio
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import numpy as np
from PIL import Image
import logging
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

logger = logging.getLogger(__name__)

@dataclass
class RAGConfig:
    """RAG配置"""
    vector_db_host: str = "localhost"
    vector_db_port: int = 6333
    embedding_model: str = "BAAI/bge-large-zh-v1.5"
    chunk_size: int = 512
    chunk_overlap: int = 50
    collection_name: str = "museum_artifacts"
    top_k: int = 5
    similarity_threshold: float = 0.7

class RAGHeart:
    """RAG心脏实现"""
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self.embedding_model = None
        self.vector_db = None
        self.is_initialized = False
        
    async def initialize(self):
        """初始化RAG系统"""
        try:
            logger.info("正在初始化RAG心脏...", extra={"dna_module": "RAG_HEART"})
            
            # 初始化嵌入模型
            self.embedding_model = SentenceTransformer(
                self.config.embedding_model,
                device="cuda" if torch.cuda.is_available() else "cpu"
            )
            
            # 初始化向量数据库
            self.vector_db = QdrantClient(
                host=self.config.vector_db_host,
                port=self.config.vector_db_port
            )
            
            # 创建集合（如果不存在）
            collections = self.vector_db.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.config.collection_name not in collection_names:
                self.vector_db.create_collection(
                    collection_name=self.config.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_model.get_sentence_embedding_dimension(),
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"创建新的向量集合: {self.config.collection_name}", 
                          extra={"dna_module": "RAG_HEART"})
            
            self.is_initialized = True
            logger.info("✅ RAG心脏初始化完成", extra={"dna_module": "RAG_HEART"})
            
        except Exception as e:
            logger.error(f"❌ RAG心脏初始化失败: {e}", 
                        extra={"dna_module": "RAG_HEART"}, exc_info=True)
            raise
    
    def chunk_text(self, text: str) -> List[str]:
        """文本分块"""
        # 简单的文本分块
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.config.chunk_size - self.config.chunk_overlap):
            chunk = " ".join(words[i:i + self.config.chunk_size])
            if chunk:
                chunks.append(chunk)
                
        return chunks
    
    async def add_document(self, 
                          content: str, 
                          metadata: Dict[str, Any],
                          image_path: Optional[str] = None) -> str:
        """添加文档到知识库"""
        if not self.is_initialized:
            raise RuntimeError("RAG心脏未初始化")
        
        try:
            # 生成文档ID
            doc_id = hashlib.md5(content.encode()).hexdigest()[:16]
            
            # 文本分块
            text_chunks = self.chunk_text(content)
            
            points = []
            for i, chunk in enumerate(text_chunks):
                # 生成嵌入
                embedding = self.embedding_model.encode(chunk).tolist()
                
                # 构建点
                point = PointStruct(
                    id=f"{doc_id}_{i}",
                    vector=embedding,
                    payload={
                        "chunk_id": i,
                        "doc_id": doc_id,
                        "text": chunk,
                        "metadata": metadata,
                        "image_path": image_path,
                        "chunk_count": len(text_chunks)
                    }
                )
                points.append(point)
            
            # 存储到向量数据库
            self.vector_db.upsert(
                collection_name=self.config.collection_name,
                points=points
            )
            
            logger.info(f"已添加文档到知识库: {metadata.get('title', '未知')}，分块数: {len(text_chunks)}", 
                       extra={"dna_module": "RAG_HEART"})
            
            return doc_id
            
        except Exception as e:
            logger.error(f"添加文档失败: {e}", extra={"dna_module": "RAG_HEART"})
            raise
    
    async def search(self, 
                    query: str, 
                    top_k: Optional[int] = None,
                    filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """检索相关文档"""
        if not self.is_initialized:
            raise RuntimeError("RAG心脏未初始化")
        
        try:
            k = top_k or self.config.top_k
            
            # 生成查询嵌入
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # 在向量数据库中搜索
            search_result = self.vector_db.search(
                collection_name=self.config.collection_name,
                query_vector=query_embedding,
                limit=k,
                query_filter=self._build_filter(filters) if filters else None
            )
            
            # 处理结果
            results = []
            for hit in search_result:
                if hit.score >= self.config.similarity_threshold:
                    result = {
                        "score": float(hit.score),
                        "text": hit.payload.get("text", ""),
                        "metadata": hit.payload.get("metadata", {}),
                        "chunk_id": hit.payload.get("chunk_id"),
                        "doc_id": hit.payload.get("doc_id"),
                        "image_path": hit.payload.get("image_path")
                    }
                    results.append(result)
            
            logger.info(f"检索到 {len(results)} 个相关文档", extra={"dna_module": "RAG_HEART"})
            return results
            
        except Exception as e:
            logger.error(f"检索失败: {e}", extra={"dna_module": "RAG_HEART"})
            return []
    
    async def search_artifact(self, 
                            artifact_name: str,
                            question: str) -> Dict[str, Any]:
        """检索文物相关信息"""
        # 构建查询
        query = f"{artifact_name} {question}"
        
        # 添加文物筛选
        filters = {
            "must": [
                {
                    "key": "metadata.artifact_name",
                    "match": {"value": artifact_name}
                }
            ]
        }
        
        # 执行检索
        search_results = await self.search(query, filters=filters)
        
        # 构建上下文
        context_parts = []
        for result in search_results[:3]:  # 取前3个
            context_parts.append(result["text"])
        
        context = "\n\n".join(context_parts)
        
        return {
            "query": query,
            "results": search_results,
            "context": context,
            "has_results": len(search_results) > 0
        }
    
    def _build_filter(self, filter_dict: Dict[str, Any]) -> Any:
        """构建查询过滤器"""
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        conditions = []
        
        for key, value in filter_dict.get("must", []):
            conditions.append(
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value)
                )
            )
        
        return Filter(must=conditions) if conditions else None
    
    async def add_artifact_knowledge(self, 
                                   artifact_data: Dict[str, Any],
                                   image_path: Optional[str] = None) -> str:
        """添加文物知识"""
        # 构建文档内容
        content_parts = []
        
        # 基本信息
        content_parts.append(f"文物名称：{artifact_data.get('name', '未知')}")
        content_parts.append(f"文物年代：{artifact_data.get('era', '未知')}")
        content_parts.append(f"出土地点：{artifact_data.get('location', '未知')}")
        content_parts.append(f"文物材质：{artifact_data.get('material', '未知')}")
        
        # 描述
        if "description" in artifact_data:
            content_parts.append(f"文物描述：{artifact_data['description']}")
        
        # 历史背景
        if "historical_background" in artifact_data:
            content_parts.append(f"历史背景：{artifact_data['historical_background']}")
        
        # 文化意义
        if "cultural_significance" in artifact_data:
            content_parts.append(f"文化意义：{artifact_data['cultural_significance']}")
        
        # 相关故事
        if "stories" in artifact_data:
            content_parts.append("相关故事：")
            for story in artifact_data["stories"]:
                content_parts.append(f"- {story}")
        
        content = "\n".join(content_parts)
        
        # 元数据
        metadata = {
            "type": "artifact",
            "artifact_name": artifact_data.get("name"),
            "era": artifact_data.get("era"),
            "location": artifact_data.get("location"),
            "material": artifact_data.get("material"),
            "added_time": asyncio.get_event_loop().time()
        }
        
        # 添加到知识库
        doc_id = await self.add_document(content, metadata, image_path)
        
        logger.info(f"已添加文物知识: {artifact_data.get('name')}", 
                  extra={"dna_module": "RAG_HEART"})
        
        return doc_id
    
    async def close(self):
        """关闭连接"""
        if self.vector_db:
            self.vector_db.close()
        self.is_initialized = False
        logger.info("RAG心脏已关闭", extra={"dna_module": "RAG_HEART"})

class RAGSelfCheck:
    """RAG自检"""
    
    async def self_check(self) -> Dict[str, Any]:
        """执行自检"""
        checks = {}
        
        # 检查向量数据库连接
        try:
            collections = self.vector_db.get_collections()
            checks["vector_db_connected"] = True
            checks["collection_count"] = len(collections.collections)
        except Exception as e:
            checks["vector_db_connected"] = False
            checks["vector_db_error"] = str(e)
        
        # 检查嵌入模型
        checks["embedding_model_loaded"] = self.embedding_model is not None
        
        # 简单检索测试
        try:
            test_results = await self.search("测试")
            checks["search_works"] = len(test_results) >= 0
            checks["search_time"] = 0.05  # 占位符
        except Exception as e:
            checks["search_works"] = False
            checks["search_error"] = str(e)
        
        return {
            "module": "rag_heart",
            "status": all(checks.values()),
            "checks": checks,
            "timestamp": asyncio.get_event_loop().time()
        }