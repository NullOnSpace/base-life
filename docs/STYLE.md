
# Python 代码风格指南

本指南旨在确保 Python 代码符合 **flake8**（样式检查）、**black**（代码格式化）和 **pylance**（类型检查与智能提示）的要求，保持代码一致性、可读性和可维护性。

---

## 1. 格式化与缩进

### 1.1 缩进
- 使用 **4 个空格**，禁止使用制表符（Tab）。
- 续行应使用括号、方括号或大括号内的隐式续行，并适当对齐。

```python
# 正确
result = some_function_that_takes_arguments(
    'first argument', 'second argument', 'third argument'
)

# 错误（混用制表符或空格不足）
result = some_function_that_takes_arguments(
  'first argument', 'second argument', 'third argument'
)
```

### 1.2 行最大长度
- **88 字符**（black 默认）。
- flake8 通过 `max-line-length = 88` 配置兼容。

### 1.3 代码格式化
- 使用 **black** 自动格式化，不用手动调整空格、换行等。
- 在提交前运行 `black .` 即可。

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
# 正确
import os
import sys

import requests
from flask import Flask

from mymodule import helper

# 错误
import os, sys
from mymodule import *
```

---

## 4. 命名规范

| 类型          | 规范             | 示例                    |
| ------------- | ---------------- | ----------------------- |
| 变量          | 小写 + 下划线    | `user_name`, `total`    |
| 常量          | 大写 + 下划线    | `MAX_SIZE`, `API_KEY`   |
| 函数          | 小写 + 下划线    | `get_data()`, `save()`  |
| 类            | 驼峰（CapWords） | `UserProfile`, `Client` |
| 私有属性/方法 | 前导下划线       | `_internal`, `_parse()` |
| 保护属性      | 单前导下划线     | `_protected`            |
| 魔术方法      | 双前导和双后缀   | `__init__`, `__str__`   |

```python
class Car:
    WHEELS = 4  # 常量

    def __init__(self, model):
        self.model = model
        self._engine_status = 'off'  # 私有

    def start(self):
        self._ignite()

    def _ignite(self):  # 内部方法
        pass
```

---

## 5. 表达式与语句

### 5.1 空格使用（根据 Black）
- 二元运算符两边加空格：`a + b`
- 赋值符号两边加空格：`x = 1`
- 函数参数默认值 `=` 两边不加空格：`def func(param=1)`
- 关键字参数不加空格：`func(param=1)`

```python
# 正确
x = (1 + 2) * 3
def greet(name: str = "World"):
    return f"Hello, {name}"

# 错误（Black 会纠正）
x=(1+2)*3
def greet(name:str="World"):
    pass
```

### 5.2 比较操作
- 使用 `is` 或 `is not` 与 `None`、`True`、`False` 比较。
- 避免与布尔值直接比较（`if x is True` → `if x`）。

```python
# 正确
if value is None:
    pass

if done:
    pass

# 错误
if value == None:
    pass

if done == True:
    pass
```

### 5.3 列表推导与生成器
- 保持简单，复杂逻辑使用普通循环。

```python
# 可接受
squares = [x**2 for x in range(10)]

# 过于复杂（易读性差）
result = [x for x in items if x['type'] == 'A' and x['value'] > 10 and some_condition(x)]
```

---

## 6. 类型注解（满足 Pylance）

### 6.1 基本类型注解
- 为函数参数和返回值添加类型注解。
- 使用 `from typing import ...` 提供复杂类型。

```python
from typing import List, Optional, Dict

def process_items(items: List[str], max_count: Optional[int] = None) -> Dict[str, int]:
    result = {}
    # ...
    return result
```

### 6.2 变量注解
- 复杂类型变量可注解以提升 Pylance 推断。

```python
data: List[Dict[str, int]] = []
```

### 6.3 类型别名
```python
UserId = int
UserDict = Dict[str, str]
```

### 6.4 避免 `Any`（尽量明确）
```python
def handle(data: Any):  # 不推荐
    pass
```

---

## 7. 函数与类设计

### 7.1 函数
- 函数应短小、单一职责。
- 参数尽量少（超过5个考虑封装为数据类或字典）。

```python
# 好
def calculate_area(length: float, width: float) -> float:
    return length * width

# 避免
def process_and_save_and_notify(data, path, email, max_retry, timeout):
    pass
```

### 7.2 类
- 遵循单一职责原则。
- 除非必要，避免使用 `@staticmethod`。

```python
class ReportGenerator:
    def __init__(self, data: List[int]):
        self.data = data

    def generate(self) -> str:
        pass
```

---

## 8. 注释与文档字符串

### 8.1 文档字符串（使用 Google 或 NumPy 风格）
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
    # ...
```

### 8.2 行内注释
- 仅用于解释复杂的逻辑，不要解释明显的操作。
- 注释与代码至少两个空格分隔。

```python
x = x + 1  # 补偿偏移量
```

---

## 9. 工具配置

### 9.1 pyproject.toml（推荐统一配置）

```toml
[tool.black]
line-length = 88
target-version = ['py39']  # 根据项目实际 Python 版本调整

[tool.flake8]
max-line-length = 88
extend-ignore = ["E203"]   # 因 black 与 flake8 对切片空格规则冲突

[tool.pylance]
# Pylance 通常通过 VS Code 设置或 pyrightconfig.json 配置
# 以下为推送到 pyright 的配置（兼容 pylance）
typeCheckingMode = "basic"
reportMissingImports = true
reportMissingTypeStubs = false
```

### 9.2 可选配置文件 `.flake8`
```ini
[flake8]
max-line-length = 88
extend-ignore = E203
```

---

## 10. 检查与自动化

- **提交前运行**：
  ```bash
  black .
  flake8 .
  ```
- **在 CI 中加入**：
  ```yaml
  - name: Lint with flake8
    run: flake8 .
  - name: Check formatting with black
    run: black --check .
  ```
- 使用 **pre-commit hooks** 自动格式化。

---

## 11. 常见错误及避免

| flake8 代码 | 说明                    | 避免方法                 |
| ----------- | ----------------------- | ------------------------ |
| E501        | 行过长                  | 自动格式化（black）      |
| E302        | 函数/类前缺少两个空行   | 遵守空行规则             |
| F401        | 导入未使用              | 删除或使用 `__all__`     |
| F841        | 变量赋值未使用          | 删除或用 `_` 占位        |
| E203        | 切片中空格与 black 冲突 | 在 flake8 中 ignore E203 |

---

## 12. 示例代码（符合全部规则）

```python
"""用户管理模块示例。"""

from typing import Dict, List, Optional


class User:
    """用户类，存储基本信息。"""

    DEFAULT_AVATAR = "default.png"

    def __init__(self, user_id: int, name: str) -> None:
        self.user_id = user_id
        self.name = name
        self._active = True

    def activate(self) -> None:
        """激活用户。"""
        self._active = True

    def deactivate(self) -> None:
        """停用用户。"""
        self._active = False


def find_active_users(users: List[User]) -> List[User]:
    """返回所有活跃用户。"""
    return [user for user in users if user._active]  # 私有属性访问仅限示例


def main() -> None:
    user = User(1, "Alice")
    user.activate()


if __name__ == "__main__":
    main()
```

---

## 13. 常见问题（FAQ）

### Q1: Black 和 flake8 规则冲突怎么办？
在 `.flake8` 或 `pyproject.toml` 中设置 `extend-ignore = E203`（切片空格问题），并保持 `max-line-length = 88`。

### Q2: Pylance 提示类型错误但代码能运行？
说明类型不一致，应修复（例如添加 `Optional`）。Pylance 基于类型提示检验，不影响运行时，但强烈建议遵守。

### Q3: 如何让团队统一配置？
提交 `pyproject.toml` 和 `.pre-commit-config.yaml` 到仓库，并安装 pre-commit 钩子。

---

