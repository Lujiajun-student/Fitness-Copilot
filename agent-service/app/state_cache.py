"""Redis JSON snapshots of generation state, isolated by user and task.

Snapshots are diagnostic caches, not LangGraph execution checkpoints.
"""

import json
import os
from datetime import datetime, timezone


class StateCacheError(RuntimeError):
    pass


class RedisStateCache:
    def __init__(self, url=None, ttl=None, client=None):
        self.url = url if url is not None else os.getenv("REDIS_URL", "").strip()
        self.ttl = ttl if ttl is not None else int(os.getenv("REDIS_STATE_TTL_SECONDS", "3600"))
        if self.ttl <= 0:
            raise ValueError("REDIS_STATE_TTL_SECONDS 必须大于 0")
        self.client = client

    @property
    def enabled(self):
        return bool(self.url or self.client is not None)

    def _client(self):
        if self.client is None:
            from redis.asyncio import Redis
            self.client = Redis.from_url(self.url, decode_responses=True,
                                         socket_connect_timeout=3, socket_timeout=3)
        return self.client

    @staticmethod
    def key(user_id, task_id):
        return f"fitness:plan-state:{int(user_id)}:{task_id}"

    async def save(self, user_id, task_id, state, status="running", node=None, result=None, error=None):
        if not self.enabled:
            return
        snapshot = {"taskId": task_id, "userId": int(user_id), "status": status,
                    "node": node, "updatedAt": datetime.now(timezone.utc).isoformat(),
                    "state": state, "result": result, "error": error}
        try:
            await self._client().set(self.key(user_id, task_id),
                                     json.dumps(snapshot, ensure_ascii=False), ex=self.ttl)
        except Exception as error:
            raise StateCacheError("Redis State 缓存不可用") from error

    async def get(self, user_id, task_id):
        if not self.enabled:
            return None
        try:
            value = await self._client().get(self.key(user_id, task_id))
            return json.loads(value) if value else None
        except Exception as error:
            raise StateCacheError("Redis State 缓存不可用") from error

    async def close(self):
        if self.client is not None:
            await self.client.aclose()


async def cached_updates(graph, state, cache, user_id, task_id):
    """Save input, each node update and final/failed state for both API modes."""
    await cache.save(user_id, task_id, state)
    last_node = None
    try:
        async for update in graph.astream(dict(state), stream_mode="updates"):
            for node, changes in update.items():
                state.update(changes)
                last_node = node
                await cache.save(user_id, task_id, state, node=node)
            yield update
        # API marks completion after final document validation.
    except Exception:
        await cache.save(user_id, task_id, state, status="failed", node=last_node)
        raise
