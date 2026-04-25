# base-life 新闻抓取

简单的新闻抓取器，根据 `config.json` 中的 `sources` 抓取并结构化输出符合 `search` 关键词的新闻。

快速开始：

- 安装依赖（使用用户提供的虚拟环境）：

```bash
/home/hikaru/.virtualenvs/base-life/bin/python3 -m pip install -r requirements.txt
```

- 运行：

```bash
/home/hikaru/.virtualenvs/base-life/bin/python3 main.py config.json
```

输出为 JSON 列表，每项包含 `source`, `url`, `title`, `pub`, `content`。

开发与提交
- 安装开发依赖：

```bash
/home/hikaru/.virtualenvs/base-life/bin/python3 -m pip install -r dev-requirements.txt
```

- 启用 pre-commit 钩子：

```bash
pre-commit install
```

在提交时会自动运行 `black` 和 `flake8`。

配置参考：请查看 [config.json](config.json) 和 [docs/START.md](docs/START.md)。
