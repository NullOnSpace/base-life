
# Python 代码风格指南

本指南旨在确保 Python 代码符合 **flake8**（样式检查）、**black**（代码格式化）和 **pylance**（类型检查与智能提示）的要求，保持代码一致性、可读性和可维护性。

项目使用 **uv** 作为包管理与任务运行工具，依赖声明集中在 `pyproject.toml`。

---

## 1. 格式化与缩进

### 1.1 缩进
- 使用 **4 个空格**，禁止使用制表符（Tab）。
- 续行应使用括号、方括号或大括号内的隐式续行，并适当对齐。

```python
result = some_function_that_takes_arguments(
    "first argument", "second argument", "third argument"
)
```

### 1.2 行最大长度
- **88 字符**（black 默认）。
- flake8 通过 `max-line-length = 88` 配置兼容。

### 1.3 代码格式化
- 使用 **black** 自动格式化，不用手动调整空格、换行等。
- 通过 uv 运行：`uv run black .`。

---

## 2. 空行与换行

- **类/顶级函数之间**：两个空行。
- **类内部方法之间**：一个空行。
- 相关功能块之间可使用一个空行，但不要过度使用。

```python
import os


class MyClass:
    def first_method(self):
        pass

    def second_method(self):
        pass


def top_level_function():
    pass
```

---

## 3. 导入语句

### 3.1 导入顺序
1. 标准库导入
2. 第三方库导入
3. 本地应用/库导入

每组之间用一个空行分隔。

### 3.2 导入规范
- 禁止 `import *`（会触发 flake8 的 F403）。
- 尽量使用绝对导入。
- 每行一个导入（除非使用括号进行多行导入）。

```python
import asyncio
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

from base_life import scraper
```

禁止的写法：
```python
import os, sys  # 多个导入在同一行
from mymodule import *  # 星号导入
```

---

## 4. 命名规范

| 类型          | 规范             | 示例                    |
| ------------- | ---------------- | ----------------------- |
| 变量          | 小写 + 下划线    | `user_name`, `total`    |
| 常量          | 大写 + 下划线    | `MAX_SIZE`, `API_KEY`   |
| 函数          | 小写 + 下划线    | `get_data()`, `save()`  |
| 类            | 驼峰（CapWords） | `NewsItem`, `Client`    |
| 私有属性/方法 | 前导下划线       | `_internal`, `_parse()` |
| 魔术方法      | 双前导和双后缀   | `__init__`, `__str__`   |

```python
class NewsItem:
    DEFAULT_SOURCE = "unknown"

    def __init__(self, title: str) -> None:
        self.title = title
        self._active = True

    def activate(self) -> None:
        self._active = True

    def _validate(self) -> bool:
        return len(self.title) > 0
```

---

## 5. 表达式与语句

### 5.1 空格使用（根据 Black）
- 二元运算符两边加空格：`a + b`
- 赋值符号两边加空格：`x = 1`
- 函数参数默认值 `=` 两边不加空格：`def func(param=1)`
- 关键字参数不加空格：`func(param=1)`

```python
x = (1 + 2) * 3

def greet(name: str = "World"):
    return f"Hello, {name}"
```

### 5.2 比较操作
- 使用 `is` 或 `is not` 与 `None`、`True`、`False` 比较。
- 避免与布尔值直接比较（`if x is True` → `if x`）。

```python
if value is None:
    pass

if done:
    pass
```

### 5.3 列表推导与生成器
- 保持简单，复杂逻辑使用普通循环。

```python
squares = [x**2 for x in range(10)]
```

---

## 6. 类型注解（满足 Pylance）

### 6.1 基本类型注解
- 为函数参数和返回值添加类型注解。
- Python 3.12+ 可直接使用 `list[str]`、`dict[str, int]` 等泛型语法，无需从 `typing` 导入。

```python
def process_items(items: list[str], max_count: int | None = None) -> dict[str, int]:
    result = {}
    return result
```

- 对于复杂类型（如 `Callable`、`TypedDict`），仍需从 `typing` 导入。

### 6.2 变量注解
- 复杂类型变量可注解以提升 Pylance 推断。

```python
data: list[dict[str, int]] = []
```

### 6.3 避免 `Any`（尽量明确）
- `Any` 会绕过类型检查，仅在真正无法确定类型时使用。
- 函数返回值包含混合类型时应使用更精确的类型（如 `dict[str, Any]`）。

---

## 7. 函数与类设计

### 7.1 函数
- 函数应短小、单一职责。
- 参数尽量少（超过 5 个考虑封装为 dataclass 或字典）。

```python
def calculate_area(length: float, width: float) -> float:
    return length * width
```

### 7.2 类
- 遵循单一职责原则。
- 使用 `@dataclass` 定义简单数据容器。

```python
from dataclasses import dataclass

@dataclass
class NewsItem:
    source: str | None = None
    url: str | None = None
    title: str | None = None
    filtered: bool = False
```

---

## 8. 注释与文档字符串

### 9.1 文档字符串（Google 风格）
```python
def fetch_user(user_id: int) -> dict:
    """根据用户 ID 获取用户资料。

    Args:
        user_id: 用户的唯一标识。

    Returns:
        包含用户信息的字典，若用户不存在则返回空字典。

    Raises:
        ValueError: 当 user_id 为负数时抛出。
    """
    if user_id < 0:
        raise ValueError("user_id 不能为负数")
```

### 9.2 行内注释
- 仅用于解释复杂的逻辑，不要解释明显的操作。
- 注释与代码至少两个空格分隔。

```python
x = x + 1  # 补偿偏移量
```

---

## 10. 工具配置

项目使用 `pyproject.toml` 作为统一配置文件，结合 **uv** 管理。

### 10.1 pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "base-life"
version = "0.1.0"
description = "Simple news scraper"
requires-python = ">=3.12"
dependencies = [
    "aiohttp>=3.9,<4",
    "beautifulsoup4>=4.12,<5",
    "lxml>=5.0,<7",
]

[dependency-groups]
dev = [
    "black>=24.0",
    "flake8>=7.0",
]

[tool.black]
line-length = 88
target-version = ['py312']

[tool.flake8]
max-line-length = 88
extend-ignore = ['E203']
```

### 10.2 uv 常用命令

| 操作                  | 命令                             |
| --------------------- | -------------------------------- |
| 创建虚拟环境          | `uv venv`                        |
| 安装项目依赖          | `uv sync`                        |
| 添加运行依赖          | `uv add <package>`               |
| 添加开发依赖          | `uv add --dev <package>`         |
| 移除依赖              | `uv remove <package>`            |
| 运行脚本              | `uv run python main.py`          |
| 运行格式化            | `uv run black .`                 |
| 运行 lint             | `uv run flake8 main.py base_life/` |
| 锁定依赖              | `uv lock`（自动生成 uv.lock）    |

> **注意**：flake8 默认不读取 `pyproject.toml`，需确保运行时传入 `--max-line-length=88 --extend-ignore=E203`，或创建 `.flake8` 配置文件：
> ```ini
> [flake8]
> max-line-length = 88
> extend-ignore = E203
> ```

---

## 11. 检查与自动化

### 11.1 提交前检查
```bash
uv run black .
uv run flake8 --max-line-length=88 --extend-ignore=E203 main.py base_life/
```

### 11.2 CI 配置示例
```yaml
steps:
  - name: Install uv
    uses: astral-sh/setup-uv@v4
  - name: Install dependencies
    run: uv sync
  - name: Check formatting
    run: uv run black --check .
  - name: Lint
    run: uv run flake8 --max-line-length=88 --extend-ignore=E203 main.py base_life/
```

---

## 12. 常见错误及避免

| flake8 代码 | 说明                    | 避免方法                 |
| ----------- | ----------------------- | ------------------------ |
| E501        | 行过长                  | 自动格式化（black）      |
| E302        | 函数/类前缺少两个空行   | 遵守空行规则             |
| F401        | 导入未使用              | 删除或使用 `__all__`     |
| F841        | 变量赋值未使用          | 删除或用 `_` 占位        |
| E203        | 切片中空格与 black 冲突 | 在 flake8 中 ignore E203 |

---

## 8. 异步编程规范

本项目大量使用 `asyncio` 和 `aiohttp`，需遵守以下规范：

### 8.1 async/await 使用
- 所有 I/O 操作（HTTP 请求、文件读取）应使用 async 函数。
- 同步阻塞调用不应出现在异步代码中。
- 使用 `asyncio.gather` 并发执行多个异步任务，而非逐个 `await`。

```python
async def fetch_multiple(urls: list[str]) -> list[str]:
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_one(session, url) for url in urls]
        return await asyncio.gather(*tasks)
```

### 8.2 并发控制
- 使用 `asyncio.Semaphore` 限制并发数量，避免压垮目标服务器。
- `aiohttp.TCPConnector(limit_per_host=N)` 控制每站点连接数。

```python
sem = asyncio.Semaphore(8)
async with sem:
    result = await fetch_one(session, url)
```

### 8.3 异常处理
- 异步网络请求只捕获预期的异常：`aiohttp.ClientError`、`asyncio.TimeoutError`。
- 禁止 `except Exception`（会吞掉所有异常，包括调试信号）。

```python
try:
    async with session.get(url) as resp:
        text = await resp.text()
except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
    logger.warning("Failed to fetch %s: %s", url, exc)
    return None
```

### 8.4 事件循环管理
- 顶层同步入口使用 `asyncio.run()` 启动事件循环。
- 不要在已有事件循环中再次调用 `asyncio.run()`。
- 不要创建未关闭的 `asyncio.new_event_loop()`（资源泄漏）。

```python
def fetch_source(source: dict[str, Any]) -> list[NewsItem]:
    return asyncio.run(parse_source(source))
```

---

## 13. 常见问题（FAQ）

### Q1: Black 和 flake8 规则冲突怎么办？
在 `pyproject.toml` 中设置 `extend-ignore = E203`（切片空格问题），并保持 `max-line-length = 88`。运行 flake8 时需传入对应参数，或创建 `.flake8` 文件。

### Q2: Pylance 提示类型错误但代码能运行？
说明类型不一致，应修复（例如添加 `Optional` 或使用 `X | None`）。Pylance 基于类型提示检验，不影响运行时，但强烈建议遵守。

### Q3: uv 和 pip 有什么区别？
uv 是 Astral 开发的极速 Python 包管理器（用 Rust 编写），替代 pip + pip-tools + virtualenv。核心优势：
- 依赖解析速度比 pip 快 10-100 倍
- 自动管理虚拟环境（`uv sync` 即安装+创建 venv）
- 通过 `uv.lock` 保证依赖可复现
- 内置 `uv run` 直接在项目环境中执行命令

### Q4: 如何让团队统一配置？
提交 `pyproject.toml` 和 `uv.lock` 到仓库。团队成员只需运行 `uv sync` 即可安装完全一致的依赖。

