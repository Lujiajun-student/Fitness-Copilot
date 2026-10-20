"""Run LangGraph outside the HTTP server. Redis holds progress and results."""

import asyncio
import logging
from contextlib import suppress
from uuid import uuid4

from app.plan_document import build_generation_response
from app.state_cache import RedisStateCache
from app.task_queue import celery_app, TASK_TIMEOUT
from app.workflow import plan_graph

logger = logging.getLogger(__name__)


async def execute_plan(user_id, task_id, state, graph=None, cache=None):
    cache = cache or RedisStateCache()
    graph = graph or plan_graph
    last_node = "planner"
    lock_key = cache.key(user_id, task_id) + ":execution-lock"
    lock_owner = str(uuid4())
    heartbeat = None
    acquired = False
    try:
        snapshot = await cache.get(user_id, task_id)
        if snapshot and snapshot["status"] in ("completed", "failed"):
            return True
        acquired = await cache._client().set(lock_key, lock_owner, nx=True, ex=TASK_TIMEOUT + 60)
        if not acquired:
            return False
        await cache.save(user_id, task_id, state, node=last_node)

        async def keep_alive():
            while True:
                await asyncio.sleep(15)
                await cache.save(user_id, task_id, state, node=last_node)

        async def generate():
            nonlocal last_node
            async for update in graph.astream(dict(state), stream_mode="updates"):
                for node, changes in update.items():
                    state.update(changes)
                    last_node = node
                    await cache.save(user_id, task_id, state, node=node)
            return {**build_generation_response(state["goal"], state["profile"], state), "taskId": task_id}

        heartbeat = asyncio.create_task(keep_alive())
        try:
            result = await asyncio.wait_for(generate(), timeout=TASK_TIMEOUT)
        finally:
            heartbeat.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat
            heartbeat = None
        await cache.save(user_id, task_id, state, status="completed", node=last_node, result=result)
        return True
    except Exception as error:
        # Detailed provider errors stay in server logs, not user-facing task data.
        logger.exception("Plan generation failed: task=%s", task_id)
        message = "生成任务超过时间上限，请重试" if isinstance(error, asyncio.TimeoutError) else "计划生成失败，请检查服务配置或稍后重试"
        await cache.save(user_id, task_id, state, status="failed", node=last_node, error=message)
        return True
    finally:
        if heartbeat is not None:
            heartbeat.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat
        if acquired:
            await cache._client().eval("if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end", 1, lock_key, lock_owner)
        await cache.close()


@celery_app.task(bind=True, name="fitness.generate_plan", max_retries=None)
def generate_plan_task(self, user_id, task_id, state):
    if not asyncio.run(execute_plan(user_id, task_id, state)):
        # Duplicate delivery must wait for the existing worker, not run concurrently.
        raise self.retry(countdown=60)
