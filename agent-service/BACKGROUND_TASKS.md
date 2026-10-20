# 独立后台计划生成

## 启动

在 agent-service 目录安装 requirements.txt，并启动 Redis：

```powershell
docker compose up -d redis
```

在 .env 配置 REDIS_URL=redis://127.0.0.1:6379/0、REDIS_STATE_TTL_SECONDS=3600、PLAN_TASK_TIMEOUT_SECONDS=1800。状态 TTL 应明显大于任务时间上限及排队时间。配置 DeepSeek 和 Java 后端地址。

分别启动 API 和独立 Worker：

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
.venv\Scripts\python.exe -m celery -A app.task_queue:celery_app worker --pool=solo --loglevel=info
```

Windows 本地使用 solo，服务器 Linux 可使用 prefork 和合适的 concurrency。Worker 和 API 必须使用相同 Redis 配置和源码版本。solo 同时执行一个任务，其他任务排队。

## 接口和前端

- POST /api/v1/plans/generate 返回 202 和 taskId，不等待模型。请求体为 goal 和可选 UUID requestId；同一用户的同一 requestId 在缓存有效期内只入队一次，目标不同返回 409。
- GET /api/v1/plans/tasks/{taskId}/state 获取 queued/running/completed/failed、State、结果及错误。所有访问通过 Java 后端认证，并按用户隔离。
- GET /api/v1/plans/tasks/{taskId} 返回精简进度和完成后的结果，前端轮询使用此接口，避免每次传输完整中间 State。
- GET /api/v1/plans/tasks/{taskId}/events 订阅 SSE，支持重新订阅已完成任务，并发送心跳。
- 原 POST /api/v1/plans/generate/stream 兼容保留：先提交，再订阅；断开不会停止 Worker。

前端默认短轮询（3 秒），每次 HTTP 请求超时 10 秒；网络问题会重试。taskId 按用户存入 localStorage，刷新后打开私人助理页恢复。离开页面会中止查询，后台任务继续执行。完成后前端缓存计划并调用 Java 接口持久化，保存成功后清除任务 ID。离线期间结果保存在 Redis，须在 TTL 内回来保存。

## 执行和边界

Worker 每个节点更新 State，15 秒刷新一次心跳和 TTL；生成有整体时间上限。失败与最终文档校验错误记录 failed。晚确认、Worker 丢失后重新投递及用户任务执行锁用于减少任务丢失和重复执行；已完成/失败任务重复投递会直接退出。

目前没有 LangGraph Checkpointer，Worker 崩溃后重新投递会从头执行，不是断点续跑；可能再次消耗模型 Token。该队列采用至少一次投递语义，不承诺 exactly-once。Redis 是队列和短期结果存储，生产环境需配置持久化、访问控制、容量和备份。API 与 Worker 不共享 Bearer Token，队列中只包含生成所需用户数据，应保护 Redis。

测试：.venv\Scripts\python.exe -m unittest discover -s tests -v。包含不依赖真实 DeepSeek/Redis 的后台完成、幂等提交、用户隔离、SSE 重连和失败测试。
