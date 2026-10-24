# RAG 知识库维护

专项 Agent 在调用 DeepSeek 生成方案前，经 MCP 执行父子分块检索并注入 `rag_knowledge`。PDF 离线提取后写入 SQLite，Markdown 项目规则作为补充知识。重排采用独立常驻进程中的本地 CrossEncoder，默认 `BAAI/bge-reranker-v2-m3`，不调用 DeepSeek、不生成重排文本。模型处理查询与子块文本对，输出对应的相关性分数；不是分别计算两个向量的相似度。模型首次启动需联网下载，有缓存后可离线运行；失败时词法降级会明确标识。

检索范围严格隔离：力量仅 strength；体能仅 endurance；营养仅 nutrition。范围由服务端固定配置，模型不能通过查询文本扩大权限。旧 sports_training、human_science、sports_nutrition 目录保留但不再检索。不要把整本跨学科教材混放在专库中；按主题审核后分别整理。

当前为所有用户共享的只读公共专业资料库，不支持用户上传私有文档。用户档案和计划只经登录鉴权读取，任务缓存按用户 ID 与任务 ID 隔离，不能写入公共知识库。当前没有企业 tenantId 或私有文档租户过滤器，不能宣称已支持企业多租户私库。若将来新增私库，应从服务端登录身份确定 tenantId/userId，检索前同时过滤租户、所有者、角色及发布状态；不能依赖提示词或先全库检索再过滤。

可收录主题：strength 收录抗阻训练、功能解剖、生物力学、神经肌肉控制和动作学习；endurance 收录运动生理、心肺耐力、强度分区、疲劳恢复及运动环境；nutrition 收录基础/运动营养、食物成分、三餐搭配、过敏与不耐受。运动神经科学只选与动作控制、协调和平衡有关的内容，不纳入疾病诊断和康复治疗处方。

PDF 通过 `app.rag_index` 导入，Word、网页、CSV 仍需转换。扫描 PDF 不自动 OCR，无文本页不入库；现有六份 PDF 均有文本层。优先使用权威指南、专业机构立场声明、系统综述和获得授权的教材摘要；不把营销内容或未经核验的模型生成文本当作专业依据。每篇记录标题、原始 URL/DOI、出版日期与版本、适用人群、局限、授权信息、审核人和审核日期。检索隔离是按角色元数据执行，不自动证明文档主题正确性。

## 入库及检索参数

在项目根目录 `docs/rag-manifest.json` 登记文件、角色、年份、来源、许可；可用 `pages` 数组指定物理 PDF 页码（从 1 开始，不是印刷页码）。在 agent-service 目录运行：

```powershell
pip install -r requirements.txt
python -m app.rag_index --docs ../docs --manifest ../docs/rag-manifest.json
```

默认索引 `agent-service/data/rag.sqlite3`，可通过 `RAG_INDEX_PATH` 指定。全量清单在同一个事务中替换，失败回滚；相同源文件以 SHA-256 标识，重复导入不累积副本。索引文件不提交 Git。Docker API 和 Worker 只读挂载本地 `agent-service/data`，需先入库，再运行/重建容器。

流程：public 租户和 Agent 角色预过滤 → 子块 BM25 召回最多 50 条 → CrossEncoder 成对评分重排 → 按父块去重 → 最多返回 Top-K=10 个父块。没有匹配时不凑数。父块按物理页内段落边界切分，上限 1800 字符；子块上限 450 字符、重叠 80 字符。保留父子 ID、命中子块、页码、来源、年份、许可、召回分数、重排分数。中文查询做常见运动术语英文扩展，便于召回英文 PDF；不是完整的跨语言向量检索。

默认 `RAG_RERANK_PROVIDER=cross-encoder`，通过 `RAG_RERANK_URL` 访问常驻服务（本地默认 http://127.0.0.1:8002）。`RAG_RERANK_TIMEOUT_SECONDS` 默认 120 秒，超时、服务异常或分数无效时降级词法排序，返回 `reranker=lexical-fallback` 和 `rerankError=cross-encoder-unavailable`。设为 `lexical` 可以主动只用词法。有效模型评分返回 `reranker=cross-encoder`。分数按原候选顺序一一对应，只接受数量匹配的有限标量，不接受新文档、ID 或生成文本，也不以旧 LLM 的 0..100 范围过滤负分。模型配置 batch_size 默认 8、最大输入长度 512 token，过长输入由分词器截断；原始查询不做英文扩展后再送模型。MCP/工作流统一 Top-K=10，规划 Agent 不检索，最终 `content` 是父块，`matchedChildContent` 是命中的子块。启动说明见上一级 README。

当前六份文档已完成机器提取试入库，均标记 `machine-extracted-unreviewed`，不是人工专业审核结论。体能资料使用保守的英文关键词规则排除显式抗阻/肌肉强化块；此规则不能保证所有跨学科内容被语义排除，正式使用前需人工确认并通过 `pages` 限定。双栏、公式、表格和旧版建议尤其需要审核；数值、单位和限定条件不明确时不得当作具体处方依据。非商业许可文件不可因进入索引就视为获得商业授权。

新增 Markdown 规则仍放在对应 knowledge 目录，添加标题、来源和审核日期。按标题/段落构成不超过 1000 字符的父块，再切子块，修改后即时读取。

本库包含公开资料的简短中文摘要和明确标注的项目应用规则，不是《运动训练学》《运动营养学》等教材全文，也没有宣称专业审核认证。来源 URL 对应公开资料；“项目应用规则”是产品约束，不应冒充原指南结论。完整教材等资料需获得授权后整理入库。原始内部英文规则仍可检索。

执行测试：在 agent-service 目录运行 `python -m unittest discover -s tests -v`。
