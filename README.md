# base-life 新闻抓取

[![CI](https://github.com/NullOnSpace/base-life/actions/workflows/ci.yml/badge.svg)](https://github.com/NullOnSpace/base-life/actions/workflows/ci.yml)
[![Ruff](https://img.shields.io/badge/lint-ruff-blue)](https://docs.astral.sh/ruff/)
[![Black](https://img.shields.io/badge/format-black-black)](https://github.com/psf/black)

简单的新闻抓取器。读取项目根目录的 `config.toml`，按 `[[sources]]` 配置抓取列表页并并发获取详情页，返回结构化的 `NewsItem` 对象供后续处理或导出。

## 快速开始

- 安装运行依赖（使用 [uv](https://docs.astral.sh/uv/) 管理）：

```bash
uv sync
```

- 运行（CLI）：

```bash
uv run base-life config.toml
```

## 输出

CLI 和库接口返回 `NewsItem` 对象（位于 `base_life.scraper`），每项包含字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `source` | `str` | 来源名称（对应配置中的 `name`） |
| `url` | `str` | 详情页 URL |
| `title` | `str | None` | 新闻标题 |
| `pub` | `str | None` | 发布时间（ISO 8601 格式） |
| `content` | `str | None` | 正文纯文本 |
| `filtered` | `bool` | 是否被搜索条件过滤（`True` = 不匹配） |
| `filter_reason` | `str | None` | 过滤原因（如 `"no match"`） |

`NewsItem` 是 dataclass，支持 `to_dict()` 方法转换为字典。

## 作为库使用

所有公共 API 位于 `base_life.scraper` 和 `base_life.cli` 两个模块。

### 常用接口一览

| 接口 | 模块 | 类型 | 说明 |
|---|---|---|---|
| `NewsItem` | `scraper` | dataclass | 抓取结果数据对象 |
| `fetch_all_sources(sources)` | `scraper` | async | 一次性抓取所有源（共享 session） |
| `fetch_source(source, search_terms, session)` | `scraper` | async | 抓取单个源（可指定搜索词） |
| `parse_source(source, session)` | `scraper` | async | 解析单个源（不自动过滤） |
| `unfiltered_items(items)` | `scraper` | sync | 从结果中筛选未过滤项 |
| `setup_logging(level)` | `scraper` | sync | 配置日志（默认读环境变量） |
| `default_headers()` | `scraper` | sync | 返回默认浏览器请求头副本 |
| `extract_pub_time(text, pub_format)` | `scraper` | sync | 从文本提取发布时间 |
| `load_config_toml(path)` | `cli` | sync | 从文件加载 TOML 配置 |
| `run(config_path)` | `cli` | sync | 读取配置并运行完整流程 |

### 抓取所有源（推荐方式）

`fetch_all_sources` 内部创建共享 `aiohttp.ClientSession`，跨源复用连接池，效率最高：

```python
import asyncio
from base_life.scraper import setup_logging, fetch_all_sources, unfiltered_items

setup_logging("DEBUG")

sources = [
    {
        "name": "water",
        "url": "https://www.somewhere.gov.cn/public/column/1234",
        "selectors": {
            "list_selector": "a.article-link",
            "title": "h1",
            "pub": "td:contains('发布日期')",
            "pub-format": "%Y-%m-%d %H:%M",
            "content": "div.article-body",
            "search": ["供水", "停水"],
        },
    },
    {
        "name": "news",
        "url": "https://www.somewhere.gov.cn/news/list",
        "selectors": {
            "list_selector": "ul.news-list a",
            "title": "h1.title",
            "pub": "span.pub-date",
            "pub-format": "%Y-%m-%d",
            "content": "div.content",
            "search": ["通知", "重要"],
        },
    },
]

items = asyncio.run(fetch_all_sources(sources))
matched = unfiltered_items(items)
for it in matched:
    print(it.title, it.pub, it.url)
```

### 抓取单个源

`fetch_source` 适合只需处理一个源的场景，可传入 `search_terms` 自动过滤：

```python
import asyncio
from base_life.scraper import fetch_source, unfiltered_items

source = {
    "name": "example",
    "url": "https://example.com/news/list",
    "selectors": {
        "list_selector": "a.news-link",
        "title": "h1",
        "pub": "time.pub",
        "pub-format": "%Y-%m-%d %H:%M:%S",
        "content": "div.article-body",
    },
}

items = asyncio.run(fetch_source(source, search_terms=["供水"]))
matched = unfiltered_items(items)
```

### 共享 session 跨源抓取

在已有 async 上下文中，可传入 `session` 参数避免反复创建连接：

```python
import aiohttp
import asyncio
from base_life.scraper import parse_source, _apply_search_filter

async def main():
    conn = aiohttp.TCPConnector(limit_per_host=5)
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        items_a = await parse_source(source_a, session=session)
        items_b = await parse_source(source_b, session=session)
        all_items = items_a + items_b

        _apply_search_filter(all_items, ["供水", "通知"])

asyncio.run(main())
```

### 从 TOML 配置运行

`base_life.cli` 提供从 TOML 文件读取配置并运行完整流程的接口：

```python
from base_life.cli import load_config_toml, run
from pathlib import Path

run("config.toml")
```

### 时间提取工具

`extract_pub_time` 可独立使用，从任意文本中按格式提取时间：

```python
from base_life.scraper import extract_pub_time

text = "发布日期：2025-04-26 10:30&nbsp;&nbsp;信息来源：xxx"
iso = extract_pub_time(text, "%Y-%m-%d %H:%M")
# => "2025-04-26T10:30:00"

text2 = "更新时间 2025/04/26"
iso2 = extract_pub_time(text2, "%Y/%m/%d")
# => "2025-04-26T00:00:00"

text3 = "发布日期：2025年04月26日"
iso3 = extract_pub_time(text3, "%Y年%m月%d日")
# => "2025-04-26T00:00:00"
```

`pub-format` 掯持标准 Python strptime 格式字符串（如 `%Y`, `%m`, `%d`, `%H`, `%M`, `%S`, `%I`, `%p`, `%B`, `%b`）。

## 功能要点


- 列表页解析支持页面中声明的 `<base href="...">`，会使用该基准解析相对链接。
- 详情页并发抓取基于 `aiohttp`（有连接与并发限制），并在请求中应用模拟浏览器默认头部。
- 每个 `source` 可在 `config.toml` 中通过 `headers` 字段覆盖或补充默认请求头。

示例 `[[sources]]`（TOML）中的 headers 覆盖与选择器：

```toml
[[sources]]
name = "example"
url = "https://example.com/news/list"

[sources.headers]
User-Agent = "MyScraper/1.0"

[sources.selectors]
list_selector = "a.article-link"
title = "h1.title"
pub = "time.pubdate"
content = "div.article-body"
```

## 配置详解（config.toml）

项目使用 TOML 配置，配置文件路径由 CLI 参数指定（默认 `config.toml`）。以下是可用字段与说明：

- `[logging]`（可选）：全局日志配置。
	- `level`：日志级别名称或数字，例如 `"INFO"`、`"DEBUG"` 或 `20`。默认 `"INFO"`。

- `[[sources]]`：来源数组表。每个来源支持以下字段：
	- `name` (string)：来源名称，用于标记 `NewsItem.source`。
	- `url` (string)：要抓取的列表页 URL。
	- `headers` (table, 可选)：覆盖或补充默认请求头，键为 HTTP 头名称。
	- `selectors` (table)：选择器和解析规则，包含：
		- `list_selector` (string)：列表页中定位链接的 CSS 选择器（例如 `a.article-link`）。
		- `title` (string)：详情页标题的 CSS 选择器。
		- `pub` (string)：详情页发布时间的选择器。
		- `pub-format` (string, 可选)：时间格式，用于解析 `pub` 中的文本，支持标准 Python strptime 格式字符串（如 `%Y-%m-%d %H:%M`、`%Y年%m月%d日`）
		- `content` (string)：详情页正文选择器，若未命中则回退到整页文本。
		- `search` (array[string], 可选)：搜索词数组；若提供，`fetch_source()` 会将不匹配任一关键词的 `NewsItem` 标记为 `filtered=true`。

示例（更完整）：请查看 [config.toml](config.toml) 文件中的注释示例。

## 日志

- 使用环境变量 `BASE_LIFE_LOG_LEVEL` 控制日志级别（例如 `DEBUG`/`INFO`/`WARNING`）：

```bash
export BASE_LIFE_LOG_LEVEL=DEBUG
uv run base-life config.toml
```

- 模块 `base_life.scraper` 提供 `setup_logging()`，调用者可直接使用以配置日志。

更多

请参考 [config.toml.example](config.toml.example) 和 [docs/START.md](docs/START.md) 了解配置格式与选择器写法。
