# base-life 新闻抓取

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

CLI 和库接口现在返回 `NewsItem` 对象（位于 `base_life.scraper`），每项包含字段：

- `source`, `url`, `title`, `pub`, `content` — 基本抓取结果。
- `filtered` (bool) — 是否被搜索条件过滤掉（`True` 表示不匹配搜索词）。
- `filter_reason` (optional) — 过滤原因说明（例如 `"no match"`）。

可编程用法示例：

```python
import asyncio
from base_life.scraper import setup_logging, fetch_all_sources

setup_logging()
sources = [
    {
        "name": "example",
        "url": "https://example.com/news/list",
        "selectors": { ... },
    },
]
items = asyncio.run(fetch_all_sources(sources))
for it in items:
    print(it.to_dict())
```

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
		- `pub-format` (string, 可选)：时间格式，用于解析 `pub` 中的文本，支持标记：`yyyy`, `mo`, `dd`, `hh`, `mi`, `ss`（例如 `"yyyy-mo-dd hh:mi"`）。
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

请参考 [config.toml](config.toml) 和 [docs/START.md](docs/START.md) 了解配置格式与选择器写法。
