# RAG 知识库维护

专项 Agent 在调用 DeepSeek 前，经 MCP 检索 Markdown 片段并注入 `rag_knowledge`。当前使用本地 BM25，不需要 Embedding、向量数据库或额外 API Key。

检索范围：力量读取 strength、sports_training、human_science；体能读取 endurance、sports_training、human_science；营养读取 nutrition、sports_nutrition、human_science。范围由服务端固定配置。

新增文档时放入对应目录，使用一级标题、二级主题标题和空行分隔段落，并添加 `来源：` 和 `审核日期：`。支持中文 Markdown；按标题和段落分片，单片不超过 1000 字符。长段落以 800 字符切分。按 BM25 排序返回 Top 3，最多 5；零分片段不返回。每次检索重新读取文件，更新即生效。

本库包含公开资料的简短中文摘要和明确标注的项目应用规则，不是《运动训练学》《运动营养学》等教材全文，也没有宣称专业审核认证。来源 URL 对应公开资料；“项目应用规则”是产品约束，不应冒充原指南结论。完整教材等资料需获得授权后整理入库。原始内部英文规则仍可检索。

执行测试：在 agent-service 目录运行 `python -m unittest discover -s tests -v`。
