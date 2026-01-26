"""向量存储测试."""
import pytest
from rag.vector_store import VectorStore


@pytest.fixture
def vector_store():
    """创建测试用向量存储."""
    return VectorStore()


def test_add_and_search_documents(vector_store):
    """测试添加和搜索文档."""
    # 添加测试文档
    documents = [
        "两数之和问题可以使用哈希表在O(n)时间内解决",
        "动态规划的核心思想是将大问题分解为小问题"
    ]
    metadatas = [
        {"problem_id": "1", "tags": ["数组", "哈希表"]},
        {"problem_id": "general", "tags": ["动态规划"]}
    ]
    ids = ["doc1", "doc2"]
    
    vector_store.add_documents(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    # 搜索测试
    results = vector_store.search("如何快速找到两个数", top_k=1)
    
    assert results is not None
    assert 'ids' in results
    assert len(results['ids'][0]) > 0


def test_get_collection_info(vector_store):
    """测试获取集合信息."""
    info = vector_store.get_collection_info()
    
    assert 'name' in info
    assert 'count' in info
    assert 'embedding_model' in info
