---
name: "coding-style"
description: "Provides guidelines and best practices for Python backend coding style, focusing on high cohesion, low coupling, type safety, and maintainability. Invoke when developing or reviewing Python code in RAG/Agent architectures."
---

# 📘 Python Backend Coding Style Guide (RAG & Agent Architecture Edition)

This coding style guide is tailored for your current project context (Python, asynchronous programming, RAG/Agent architecture). It emphasizes **high cohesion and low coupling** design principles, **type safety**, and **maintainability**.

## 1. Core Design Principles

### 1.1 High Cohesion, Low Coupling

- **Single Responsibility Principle**: Each class or function should do only one thing.
  - ✅ **Correct**: `Retriever` class is only responsible for retrieval, `PromptBuilder` class is only responsible for assembling prompts.
  - ❌ **Incorrect**: `AgentManager` is responsible for retrieval, JSON parsing, and database connection.
- **Dependency Inversion**: Modules interact through interfaces (Protocol or Abstract Class), not concrete implementations.
  - Use `Dependency Injection` to decouple components.

### 1.2 Explicit over Implicit

- All inputs and outputs must be explicitly defined through **type hints**.
- Avoid using global variables unless they are configuration constants.

### 1.3 Defensive Programming

- Never trust external input (user input, API responses, database reads).
- Perform parameter validation at the function entry point.

## 2. Naming Conventions

| Type        | Convention       | Example                              |
| :-------- | :------- | :------------------------------ |
| **Variables/Functions** | Snake Case    | `user_query`, `calculate_score` |
| **Class Names**    | Pascal Case   | `KnowledgeGraph`, `VectorStore` |
| **Constants**    | All Caps      | `MAX_RETRIES`, `API_KEY`        |
| **Private Members**  | Single Underscore Prefix   | `_internal_cache`               |
| **Async Functions**  | `a` Prefix | `astream`, `aget_response`      |

## 3. Type Hinting

Python is a dynamic language, but type hints must be enforced in large projects.

### 3.1 Basic Types

```python
def process_data(count: int, name: str, is_active: bool) -> str:
    ...
```

### 3.2 Complex Types and TypedDict

Avoid using bare dictionaries `dict`. Instead, use `TypedDict` or `Pydantic` models to define data structures, especially for RAG context or Agent state.

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

## 4. Comments and Docstrings

Comments should explain **"why"** something is done, not **"what"** is done (the code itself should explain what is done).

### 4.1 Function Docstrings

All public functions must include docstrings explaining parameters, return values, and exceptions.

```python
async def aretrieve_context(
    query: str, 
    index_name: str, 
    threshold: float = 0.7
) -> List[Document]:
    """
    Retrieves relevant document snippets from the vector database.
    
    This function performs semantic search and filters out results with similarity scores below the threshold.
    
    Args:
        query: The user's search query text.
        index_name: The target index name (e.g., 'knowledge_base').
        threshold: The minimum threshold for similarity scores, defaults to 0.7.
        
    Returns:
        A list of Document objects containing document content.
        
    Raises:
        ConnectionError: Raised when the database connection fails.
    """
    ...
```

### 4.2 Inline Comments

```python
# ❌ Bad comment: duplicates code meaning
x = x + 1  # x plus 1

# ✅ Good comment: explains business logic or reason
x = x + 1  # Compensate for index offset, because the external API returns 0-based indices, but we need to display 1-based indices
```

## 5. Asynchronous Programming Guidelines

Since the project heavily uses `asyncio`, asynchronous guidelines must be strictly followed.

### 5.1 Naming

All asynchronous functions must start with `a`.

- `def get_user(): ...` (Synchronous)
- `async def aget_user(): ...` (Asynchronous)

### 5.2 Avoid Blocking

- **Strictly prohibit** the use of synchronous I/O operations (e.g., `time.sleep`, `requests.get`, file read/write) in asynchronous functions.
- Must use `await asyncio.sleep()`, `httpx.AsyncClient`, `aiofiles`, etc.

### 5.3 Exception Handling

Catch exceptions in `async` blocks to prevent coroutine crashes.

```python
try:
    result = await some_async_operation()
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    # Execute fallback strategy
    result = get_fallback_data()
```

## 6. Error Handling and Logging

### 6.1 Custom Exceptions

Do not directly raise generic `Exception`. Define business-specific exceptions.

```python
class KnowledgeRetrievalError(Exception):
    """Raised when knowledge base retrieval fails"""
    pass
```

### 6.2 Logging Standards

Use the standard `logging` module. Prohibit the use of `print`.

```python
import logging

logger = logging.getLogger(__name__)

def process_request(req_id: str):
    logger.info(f"Starting to process request: {req_id}")
    try:
        # ... Business logic
        logger.debug("Step 1 completed")
    except Exception as e:
        logger.error(f"Request {req_id} failed: {e}", exc_info=True)
        raise
```

## 7. Code Structure Example

A standard module file structure should be as follows:

```python
"""
knowledge_retriever.py - Responsible for knowledge base retrieval and context building
"""
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class VectorRetriever:
    """
    Vector retriever, encapsulates specific vector database operations.
    """
    
    def __init__(self, client):
        self.client = client

    async def asearch(self, query: str, top_k: int) -> List[Dict]:
        """
        Performs semantic search.
        """
        if not query:
            logger.warning("Query is empty, skipping retrieval")
            return []
            
        # Simulate asynchronous call
        results = await self.client.query(query, top_k)
        return self._filter_results(results)

    def _filter_results(self, results: List[Dict]) -> List[Dict]:
        """Internal private method: filters low-scoring results"""
        return [r for r in results if r.get('score', 0) > 0.5]
```

## 8. Review Checklist

Before submitting code, ask yourself the following questions:

1. **Readability**: Are variable names immediately understandable?
2. **Decoupling**: Have I put too much functionality into one class? (e.g., writing database connection logic in API routes)
3. **Types**: Have I added type hints to all function parameters and return values?
4. **Asynchronous**: Have I used blocking calls in asynchronous functions?
5. **Comments**: Have I written docstrings for complex logic?
6. **Testing**: Is this function easy to write unit tests for? (If it's hard to test, it means coupling is too high)
