"""RAG (Retrieval-Augmented Generation) 模块.

支持:
- 向量存储 (PostgreSQL + pgvector)
- 文档检索
- 语义搜索
"""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore

from app.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# 嵌入模型
# ============================================================================

def get_embeddings() -> Embeddings:
    """
    获取嵌入模型实例.

    支持多种嵌入API:
    - OpenAI embeddings
    - 本地模型 (通过sentence-transformers)

    Returns:
        Embeddings实例
    """
    from langchain_openai import OpenAIEmbeddings

    api_key = getattr(settings, "API_KEY", None)
    if not api_key:
        raise ValueError("未设置API_KEY，无法使用嵌入模型")

    base_url = getattr(settings, "MODEL_API_URL", None)

    return OpenAIEmbeddings(
        model="text-embedding-3-small",  # 或使用其他模型
        api_key=api_key,
        base_url=base_url,
    )


# ============================================================================
# 向量存储
# ============================================================================

class SimpleVectorStore:
    """
    简单的向量存储实现 (内存存储).

    适用于开发和测试环境.
    """

    def __init__(self, embeddings: Embeddings):
        self.embeddings = embeddings
        self.documents: List[Document] = []
        self.embeddings_cache: List[List[float]] = []

    async def add_documents(self, documents: List[Document]) -> List[str]:
        """添加文档到向量存储."""
        self.documents.extend(documents)

        # 生成嵌入
        texts = [doc.page_content for doc in documents]
        embeddings_list = await self.embeddings.aembed_documents(texts)
        self.embeddings_cache.extend(embeddings_list)

        return [str(i) for i in range(len(self.documents))]

    async def similarity_search(
        self,
        query: str,
        k: int = 4,
        score_threshold: Optional[float] = None,
    ) -> List[Document]:
        """相似度搜索."""
        if not self.documents:
            return []

        # 生成查询嵌入
        query_embedding = await self.embeddings.aembed_query(query)

        # 计算相似度
        import numpy as np

        query_vec = np.array(query_embedding)
        doc_vecs = np.array(self.embeddings_cache)

        # 计算余弦相似度
        similarities = np.dot(doc_vecs, query_vec) / (
            np.linalg.norm(doc_vecs, axis=1) * np.linalg.norm(query_vec)
        )

        # 获取top k
        top_indices = similarities.argsort()[-k:][::-1]

        results = []
        for idx in top_indices:
            if score_threshold is None or similarities[idx] >= score_threshold:
                doc = self.documents[idx].copy()
                doc.metadata["score"] = float(similarities[idx])
                results.append(doc)

        return results

    @classmethod
    async def from_documents(
        cls,
        documents: List[Document],
        embeddings: Embeddings,
    ) -> "SimpleVectorStore":
        """从文档创建向量存储."""
        store = cls(embeddings)
        await store.add_documents(documents)
        return store


# ============================================================================
# 检索器
# ============================================================================

async def retrieve_relevant_docs(
    query: str,
    vector_store: Optional[VectorStore] = None,
    k: int = 4,
) -> List[Dict[str, Any]]:
    """
    检索相关文档.

    Args:
        query: 查询文本
        vector_store: 向量存储实例
        k: 返回的文档数量

    Returns:
        相关文档列表
    """
    if vector_store is None:
        logger.warning("向量存储未初始化，返回空结果")
        return []

    try:
        docs = await vector_store.similarity_search(query, k=k)

        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
            }
            for doc in docs
        ]

    except Exception as e:
        logger.error(f"文档检索失败: {e}")
        return []


# ============================================================================
# 知识库初始化
# ============================================================================

async def initialize_knowledge_base() -> SimpleVectorStore:
    """
    初始化算法知识库.

    Returns:
        向量存储实例
    """
    embeddings = get_embeddings()

    # 示例算法知识文档
    sample_docs = [
        Document(
            page_content="动态规划是一种通过把原问题分解为相对简单的子问题的方式求解复杂问题的方法。",
            metadata={"topic": "动态规划", "difficulty": "medium"},
        ),
        Document(
            page_content="双指针是一种通过使用两个指针同时遍历数组或链表来解决问题的技巧。",
            metadata={"topic": "双指针", "difficulty": "easy"},
        ),
        Document(
            page_content="二分查找是一种在有序数组中查找目标元素的高效算法，时间复杂度为O(log n)。",
            metadata={"topic": "二分查找", "difficulty": "easy"},
        ),
        Document(
            page_content="深度优先搜索(DFS)是一种用于遍历或搜索树或图的算法。",
            metadata={"topic": "DFS", "difficulty": "medium"},
        ),
        Document(
            page_content="广度优先搜索(BFS)是一种用于遍历或搜索树或图的算法，按层级遍历。",
            metadata={"topic": "BFS", "difficulty": "medium"},
        ),
    ]

    vector_store = await SimpleVectorStore.from_documents(sample_docs, embeddings)
    logger.info(f"知识库初始化完成，包含{len(sample_docs)}个文档")

    return vector_store


# ============================================================================
# 全局向量存储实例
# ============================================================================

_vector_store: Optional[SimpleVectorStore] = None


async def get_vector_store() -> SimpleVectorStore:
    """
    获取全局向量存储实例 (单例模式).

    Returns:
        向量存储实例
    """
    global _vector_store

    if _vector_store is None:
        _vector_store = await initialize_knowledge_base()

    return _vector_store


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "get_embeddings",
    "SimpleVectorStore",
    "retrieve_relevant_docs",
    "initialize_knowledge_base",
    "get_vector_store",
]
