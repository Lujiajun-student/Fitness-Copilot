# Agent 服务

Python 的 LangGraph 编排服务。它只负责计划生成工作流，不直接拥有用户和计划数据。计划生成由 DeepSeek 驱动：规划 Agent → 力量/体能 Agent 两轮协商 → Harness 安全审核 → 营养 Agent。

Agent 通过 MCP 调用受控工具，例如读取用户档案、读取训练历史、估算能量消耗、检索食物数据、提交计划和执行 Harness 校验。业务数据的最终读写权保留在 Java 后端。

当前第一版已实现：规划、力量、体能、Harness、营养五个 LangGraph 节点；力量和体能节点经过两轮有限协商后再进行 Harness 校验。计划接口通过 MCP 工具读取 Java 后端的当前用户资料和最近身体测量，并返回 30 天结构化训练与三餐计划。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env  # 若尚未存在 .env
# 编辑 .env，填写 DEEPSEEK_API_KEY
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

`.env` 已被 Git 忽略，不能提交真实密钥。可配置 `DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`（默认 `deepseek-chat`）、`DEEPSEEK_TEMPERATURE` 及 `BACKEND_URL`。

健康检查：`GET http://127.0.0.1:8001/api/health`。其中 `deepseekConfigured: true` 表示服务已读取到密钥。

生成计划：`POST http://127.0.0.1:8001/api/v1/plans/generate`，携带 Java 登录接口返回的 `Authorization: Bearer <token>`，请求体例如 `{"goal":"未来一个月减脂"}`。Java 后端须先在 `BACKEND_URL` 指向的地址运行。

生成结果暂不自动写回 Java 后端，避免在用户确认前持久化；MCP 写入工具已经预留，可在确认交互完成后调用。

## MCP 工具

- 读取：`get_current_user`、`get_latest_body_measurement`、`get_training_history`。
- 计算：`calculate_training_load`、`calculate_calorie_target`、`search_food_nutrition`。
- 安全：`validate_plan_safety`。
- 写入：`save_monthly_plan`、`save_daily_nutrition_plan`。

写入工具只应在 Harness 安全校验通过后调用。
