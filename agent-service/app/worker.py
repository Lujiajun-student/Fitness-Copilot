"""Run LangGraph outside the HTTP server. Redis holds progress and results."""

import asyncio
import logging
from contextlib import suppress
from uuid import uuid4
from time import perf_counter

from app.plan_document import build_generation_response
from app.state_cache import RedisStateCache
from app.task_queue import celery_app, TASK_TIMEOUT
from app.workflow import plan_graph
from app.diagnostics import task_id as diagnostic_task_id
from app.deepseek_client import DeepSeekResponseError, DeepSeekOutputTruncated

logger = logging.getLogger(__name__)


async def execute_plan(user_id, task_id, state, graph=None, cache=None):
    diagnostic_token = diagnostic_task_id.set(str(task_id))
    started = perf_counter()
    logger.info("task_started task=%s", task_id)
    cache = cache or RedisStateCache()
    graph = graph or plan_graph
    last_node = None
    lock_key = cache.key(user_id, task_id) + ":execution-lock"
    lock_owner = str(uuid4())
    heartbeat = None
    acquired = False
    try:
        snapshot = await cache.get(user_id, task_id)
        if snapshot and snapshot["status"] in ("completed", "failed"):
            logger.info("task_skipped task=%s status=%s", task_id, snapshot["status"])
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
                    logger.info("task_progress task=%s completed_node=%s", task_id, node)
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
        logger.info("task_completed task=%s result_type=%s elapsed_ms=%d", task_id, result.get("type"), (perf_counter() - started) * 1000)
        return True
    except Exception as error:
        # Detailed provider errors stay in server logs, not user-facing task data.
        logger.exception("task_failed task=%s last_completed_node=%s error_type=%s elapsed_ms=%d", task_id,
                         last_node, type(error).__name__, (perf_counter() - started) * 1000)
        if isinstance(error, asyncio.TimeoutError):
            message = "生成任务超过时间上限，请重试"
        elif isinstance(error, DeepSeekOutputTruncated):
            message = "AI 输出被截断，计划尚未保存，请重试并检查服务输出长度配置"
        elif isinstance(error, DeepSeekResponseError):
            message = "AI 响应不完整或格式异常，计划尚未保存，请重试；详情请查看任务日志"
        else:
            message = "计划生成失败，请检查服务配置或稍后重试"
        await cache.save(user_id, task_id, state, status="failed", node=last_node, error=message)
        return True
    finally:
        diagnostic_task_id.reset(diagnostic_token)
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
