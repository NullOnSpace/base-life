# 新闻通知推送

读取指定页面的新闻列表，将符合条件的新闻结构化输出

## 流程
- 读取config.toml中的sources键，值为列表
- 读取列表中每个消息源的定义
- 用url访问新闻列表页
- selectors键中的list_selector选择器是该列表页中的详情页的链接元素
- 访问每个详情页
- title是新闻标题的选择器
- pub是发布时间的选择器，值的示例"
                       发布日期：2026-04-23 10:16&nbsp;&nbsp;信息来源：xxxxxx&nbsp;&nbsp;【字体：<a href="javascript:doZoom(18)">大</a>&nbsp;<a href="javascript:doZoom(16)">中</a>&nbsp;<a href="javascript:doZoom(12)">小</a>"
- 发布时间需要通过pub-format定义的格式提取出来
- content为新闻内容选择器，内部可能有html标签，需要提取成纯文本
- 最后结构化返回content包含search中任一词条的新闻