# Redis State 缓存

安装更新后的 requirements.txt，并运行 Redis 服务。在 agent-service/.env 设置：

```dotenv
REDIS_URL=redis://127.0.0.1:6379/0
REDIS_STATE_TTL_SECONDS=3600
```

REDIS_URL 留空则关闭缓存。远程服务可使用带凭证的 rediss:// 地址；不要将 Redis 暴露为公开无认证服务。缓存包含身体数据和健康档案，TTL 默认一小时，每次写入刷新 TTL；不要缓存 Bearer Token。

普通生成接口返回 HTTP 202 和 taskId，Celery Worker 缓存每次节点更新、最终完成/失败状态。SSE 只订阅进度和结果。Redis Key 为 fitness:plan-state:{userId}:{taskId}；完整启动方式见 BACKGROUND_TASKS.md。

GET /api/v1/plans/tasks/{taskId}/state 携带 Authorization: Bearer Token 查询快照。服务通过 Java 后端验证身份，只读取当前用户 Key；不存在或过期返回 404。配置 Redis 后不可用将阻止生成并返回明确错误，避免悄悄失去缓存。

缓存是 JSON State 快照，不是 LangGraph Checkpointer。任务由独立 Celery Worker 运行，SSE 断开不影响执行。Worker 异常退出后可重新投递从头执行；真正从断点恢复仍需另外配置 Checkpointer。

健康接口 stateCacheEnabled 仅表示是否启用配置，不代表 Redis 连通性。测试运行：.venv\Scripts\python.exe -m unittest discover -s tests -v。
