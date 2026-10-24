# Agent 服务

## 规划简述与诊断日志

总规划节点只生成30天的日历框架，每天包含 `day`、`type` 和约30字的 `focus`，提示词内提供了力量、有氧、休息日三个单日样例。力量节点补齐力量/混合日动作，体能节点补齐有氧/恢复日并参与协商；完全休息日允许空动作列表。最终保存的计划仍包含每日详细训练和三餐，不会将简述直接当作完整计划保存。

力量、体能（包括第二轮复核）和饮食节点按每批最多5天生成，单个节点最多并发2个模型请求；每批只接收对应日期的详细计划，同时携带全月简述维持训练节奏。专属RAG每个节点调用一次，检索结果在该节点各批之间复用。若模型明确返回输出截断，本批会二分重试，直至单日；单日仍截断则明确失败，不拼接不完整JSON。全部批次通过范围、重复日期及三餐完整性检查后才合并为完整月计划，失败会取消其他尚未完成的批次请求。请求次数会增加，但避免一次要求模型输出整月明细。

分批日志包含 `batch_started`、`batch_completed`、`batch_split` 和 `batch_single_day_truncated`，可结合任务ID、节点及日期范围定位问题。

`DEEPSEEK_PLANNER_MAX_TOKENS` 默认4096，控制简述输出预算；`DEEPSEEK_MAX_TOKENS` 默认8192，控制其余节点输出预算。无需修改现有 `.env` 即可使用默认值。

日志通过 `task`、`node` 关联任务和节点，记录节点耗时、模型响应字符数、token用量、`finish_reason`，以及JSON解析失败的行列和字符位置。`llm_output_truncated` 表示模型达到输出预算，`llm_json_error` 表示JSON解析失败；不会记录用户正文、模型正文或密钥。使用Docker时运行 `docker compose logs -f agent-worker` 查看生成任务日志。日志仅供诊断，不会自动重试已经失败的任务。

Python 的 LangGraph 编排服务，使用 DeepSeek 支持上下文聊天和计划生成，不直接拥有用户业务数据。入口规划 Agent 先判断消息意图：普通聊天直接回复，计划请求才进入月度规划、力量/体能协商、Harness 建议和营养节点。

Agent 通过 MCP 调用受控工具，例如读取用户档案、读取训练历史、估算能量消耗、检索食物数据、提交计划和执行 Harness 校验。业务数据的最终读写权保留在 Java 后端。

Harness 仅提出训练建议，不再否决计划或回流重规划；建议通过 `plan.safetyNotes` 展示。30 天覆盖、三餐结构等数据格式仍需完整，避免保存不可用的计划。普通聊天不要求先填写身体资料，明确生成计划但缺少资料时会用聊天回复提示补充。

每次提交聊天时，通过登录凭证重新读取当前用户的个人档案、最新身体测量、训练记录和最新已保存月计划，作为该次任务的上下文快照。助手可回答“第 7 天吃什么”“明天几点训练”“为什么这天安排恢复”等问题；计划日期由开始日期及天数换算，今天/明天按北京时间解释。未记录的安排原因会标明为推测，没有计划或超出日期范围时不会编造。仅咨询不会修改计划。尚未保存到 Java 后端的生成结果需先完成保存，才能在后续聊天中读取。

`POST /api/v1/assistant/messages` 接受 `goal`（本次消息）、`messages`（最近最多 20 条 user/assistant 对话）和 `requestId`。后台任务、轮询及刷新恢复机制保持不变。完成结果通过 `type: chat` 和 `reply` 返回聊天，或通过 `type: plan` 和 `plan` 返回计划；前端只对计划结果执行保存，聊天不会覆盖现有计划。旧 `/api/v1/plans/generate` 地址兼容保留。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env  # 若尚未存在 .env
# 编辑 .env，填写 DEEPSEEK_API_KEY
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

计划使用 Redis + Celery 独立后台执行，切换菜单或刷新浏览器后前端会按任务 ID 恢复进度。在 `agent-service` 目录先执行 `docker compose up -d redis`，并在另一个终端启动 Worker：

```powershell
.venv\Scripts\python.exe -m celery -A app.task_queue:celery_app worker --pool=solo --loglevel=info
```

`.env` 需配置 `REDIS_URL=redis://127.0.0.1:6379/0`。`REDIS_STATE_TTL_SECONDS` 默认 86400 秒，完成结果在缓存有效期内可取回；`PLAN_TASK_TIMEOUT_SECONDS` 默认 1800 秒。后台任务详情见 `BACKGROUND_TASKS.md`。

`.env` 已被 Git 忽略，不能提交真实密钥。可配置 `DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`（默认 `deepseek-chat`）、`DEEPSEEK_TEMPERATURE` 及 `BACKEND_URL`。

健康检查：`GET http://127.0.0.1:8001/api/health`。其中 `deepseekConfigured: true` 表示服务已读取到密钥。

生成计划：`POST http://127.0.0.1:8001/api/v1/plans/generate`，携带 Java 登录接口返回的 `Authorization: Bearer <token>`，请求体例如 `{"goal":"未来一个月减脂"}`。Java 后端须先在 `BACKEND_URL` 指向的地址运行。

生成接口返回 HTTP 202 和 `taskId`。前端每 3 秒查询 `GET /api/v1/plans/tasks/{taskId}`，完成后更新本地计划并保存到 Java 后端。聊天记录、草稿、任务 ID 和进度按用户存入浏览器本地存储；菜单切换后继续查询，刷新后自动恢复。暂时断网不会重新提交已确认的任务。若后台结果尚未保存到 Java，需在 Redis 缓存有效期内返回取回结果。

## MCP 工具

RAG 已接入力量、体能和饮食节点：各节点生成前自动调用角色专属 MCP 工具，按父子分块检索：public+角色预过滤 → 子块 BM25 召回 50 → 本地 CrossEncoder 成对评分 → 父块去重 → Top-K=10。PDF 离线提取到 SQLite，Markdown 规则仍支持。检索范围严格限定：力量仅 strength、体能仅 endurance、饮食仅 nutrition。旧共享目录不再索引。规划和普通聊天不调用 RAG。工具返回结果在注入模型前再次校验角色及来源编号，跨域结果拒绝注入。入库命令、审核限制和参数详见 `knowledge/README.md`。

工具为 `retrieve_strength_knowledge`、`retrieve_endurance_knowledge`、`retrieve_nutrition_knowledge`，参数为 `query` 和 `limit`（默认及上限 10）。CrossEncoder 服务不可用或超时会返回明确标记的词法降级结果；`RAG_RERANK_TIMEOUT_SECONDS` 默认 120 秒，整个 MCP 调用额外预留 30 秒。CPU 推理可能较慢，可根据实际硬件调整。重排不调用 DeepSeek、不产生 DeepSeek Token 费用。模型实际引用的有效父块编号保存在计划 `summary.knowledge_references` 中，按角色区分；当前为节点自动检索，不是模型自主工具调用。

## 本地启动 CrossEncoder

默认使用支持中英文的 `BAAI/bge-reranker-v2-m3`。在 agent-service 目录的独立终端启动常驻重排服务：

```powershell
pip install "torch>=2.6,<3.0" --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-reranker.txt
uvicorn app.reranker_server:app --host 127.0.0.1 --port 8002 --workers 1
```

本地 `.env` 设置 `RAG_RERANK_PROVIDER=cross-encoder`、`RAG_RERANK_URL=http://127.0.0.1:8002`，删除或替换旧 `deepseek` 重排配置。`RAG_RERANK_MODEL` 可指定模型 ID 或本地模型目录，`RAG_RERANK_DEVICE=cpu`、`RAG_RERANK_BATCH_SIZE=8` 为默认值。模型首次启动自动下载并缓存；有完整缓存后可设置 `RAG_RERANK_LOCAL_ONLY=true` 禁止联网加载。重排服务只负责对候选文本评分，不读取知识库、不持有 DeepSeek 密钥，也不接收用户登录凭证。

`GET http://127.0.0.1:8002/health` 在模型成功加载后返回健康。实际检索结果 `reranker=cross-encoder` 才表示神经模型评分生效；`lexical-fallback` 表示降级，不应混淆。模型只在重排进程内加载一次，MCP 子进程通过本地 HTTP 复用它。生产中不要将该无鉴权内部服务公开到互联网。

- 读取：`get_current_user`、`get_latest_body_measurement`、`get_training_history`、`get_current_monthly_plan`。
- 计算：`calculate_training_load`、`calculate_calorie_target`、`search_food_nutrition`。
- 安全：`validate_plan_safety`。
- 写入：`save_monthly_plan`、`save_daily_nutrition_plan`。

Harness 仅提供建议，不作为写入的否决门槛；计划仍需符合完整的数据结构。
