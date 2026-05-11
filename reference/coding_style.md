这份代码规范文档是基于你当前的项目上下文（Python、异步编程、RAG/Agent 架构）量身定制的。它重点强调了**高内聚低耦合**的设计原则、**类型安全**以及**可维护性**。

你可以将此文档保存为 `CODE_STYLE_GUIDE.md` 并放在项目根目录。

***

# 📘 Python 后端代码规范指南 (RAG & Agent 架构版)

## 1. 核心设计原则

### 1.1 高内聚，低耦合

- **单一职责原则**: 每个类或函数只做一件事。
  - ✅ **正确**: `Retriever` 类只负责检索，`PromptBuilder` 类只负责组装提示词。
  - ❌ **错误**: `AgentManager` 既负责检索，又负责解析 JSON，还负责连接数据库。
- **依赖倒置**: 模块之间通过接口（Protocol 或 Abstract Class）交互，而不是具体实现。
  - 使用 `Dependency Injection` (依赖注入) 来解耦组件。

### 1.2 显式优于隐式

- 所有的输入输出必须通过**类型提示**明确定义。
- 避免使用全局变量，除非是配置常量。

### 1.3 防御性编程

- 永远不要相信外部输入（用户输入、API 响应、数据库读取）。
- 在函数入口处进行参数校验。

***

## 2. 命名规范

| 类型        | 规范       | 示例                              |
| :-------- | :------- | :------------------------------ |
| **变量/函数** | 蛇形命名法    | `user_query`, `calculate_score` |
| **类名**    | 大驼峰命名法   | `KnowledgeGraph`, `VectorStore` |
| **常量**    | 全大写      | `MAX_RETRIES`, `API_KEY`        |
| **私有成员**  | 单下划线前缀   | `_internal_cache`               |
| **异步函数**  | 加 `a` 前缀 | `astream`, `aget_response`      |

***

## 3. 类型提示

Python 是动态语言，但在大型项目中必须强制使用类型提示。

### 3.1 基础类型

```python
def process_data(count: int, name: str, is_active: bool) -> str:
    ...
```

### 3.2 复杂类型与 TypedDict

避免使用裸字典 `dict`，应使用 `TypedDict` 或 `Pydantic` 模型来定义数据结构，特别是对于 RAG 的上下文或 Agent 的状态。

```python
from typing import TypedDict, List, Optional

class Message(TypedDict):
    role: str
    content: str

class RetrievalResult(TypedDict):
    doc_id: str
    score: float
    content: str

def search(query: str, top_k: int = 5) -> List[RetrievalResult]:
    ...
```

***

## 4. 注释与文档字符串

注释应该解释\*\*“为什么”**这样做，而不是**“做了什么”\*\*（代码本身应该能说明做了什么）。

### 4.1 函数文档字符串

所有公共函数必须包含文档字符串，说明参数、返回值和异常。

```python
async def aretrieve_context(
    query: str, 
    index_name: str, 
    threshold: float = 0.7
) -> List[Document]:
    """
    从向量数据库中检索相关文档片段。
    
    该函数会执行语义搜索，并过滤掉相似度低于阈值的结果。
    
    Args:
        query: 用户的搜索查询文本。
        index_name: 目标索引名称（例如 'knowledge_base'）。
        threshold: 相似度分数的最低阈值，默认为 0.7。
        
    Returns:
        包含文档内容的 Document 对象列表。
        
    Raises:
        ConnectionError: 当数据库连接失败时抛出。
    """
    ...
```

### 4.2 行内注释

```python
# ❌ 坏注释：重复代码含义
x = x + 1  # x 加 1

# ✅ 好注释：解释业务逻辑或原因
x = x + 1  # 补偿索引偏移，因为外部 API 返回的索引是从 0 开始，但我们需要从 1 开始展示
```

***

## 5. 异步编程规范

由于项目大量使用 `asyncio`，必须严格遵守异步规范。

### 5.1 命名

所有异步函数必须以 `a` 开头。

- `def get_user(): ...` (同步)
- `async def aget_user(): ...` (异步)

### 5.2 避免阻塞

- 在异步函数中**严禁**使用同步的 IO 操作（如 `time.sleep`, `requests.get`, 文件读写）。
- 必须使用 `await asyncio.sleep()`, `httpx.AsyncClient`, `aiofiles` 等。

### 5.3 异常处理

在 `async` 块中捕获异常，防止协程崩溃。

```python
try:
    result = await some_async_operation()
except ConnectionError as e:
    logger.error(f"连接失败: {e}")
    # 执行降级策略
    result = get_fallback_data()
```

***

## 6. 错误处理与日志

### 6.1 自定义异常

不要直接抛出通用的 `Exception`，应定义业务相关的异常。

```python
class KnowledgeRetrievalError(Exception):
    """当知识库检索失败时抛出"""
    pass
```

### 6.2 日志规范

使用标准 `logging` 模块，禁止使用 `print`。

```python
import logging

logger = logging.getLogger(__name__)

def process_request(req_id: str):
    logger.info(f"开始处理请求: {req_id}")
    try:
        # ... 业务逻辑
        logger.debug("步骤 1 完成")
    except Exception as e:
        logger.error(f"请求 {req_id} 处理失败: {e}", exc_info=True)
        raise
```

***

## 7. 代码结构示例

一个标准的模块文件结构应如下所示：

```python
"""
knowledge_retriever.py - 负责处理知识库的检索与上下文构建
"""
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class VectorRetriever:
    """
    向量检索器，封装具体的向量数据库操作。
    """
    
    def __init__(self, client):
        self.client = client

    async def asearch(self, query: str, top_k: int) -> List[Dict]:
        """
        执行语义搜索。
        """
        if not query:
            logger.warning("查询为空，跳过检索")
            return []
            
        # 模拟异步调用
        results = await self.client.query(query, top_k)
        return self._filter_results(results)

    def _filter_results(self, results: List[Dict]) -> List[Dict]:
        """内部私有方法：过滤低分结果"""
        return [r for r in results if r.get('score', 0) > 0.5]
```

***

## 8. 审查清单

在提交代码前，请自问以下问题：

1. **可读性**: 变量名是否一眼就能看懂？
2. **解耦**: 我是否在一个类里塞了太多功能？（比如把数据库连接逻辑写在了 API 路由里）
3. **类型**: 我是否给所有函数参数和返回值都加了类型提示？
4. **异步**: 我是否在异步函数中使用了阻塞调用？
5. **注释**: 复杂的逻辑是否写了 `"""文档字符串"""`？
6. **测试**: 这个函数是否容易编写单元测试？（如果很难测试，说明耦合度太高）

