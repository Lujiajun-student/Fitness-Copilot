import asyncio
import json
import unittest
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from app import main
from app.state_cache import RedisStateCache
from app.worker import execute_plan


class MemoryRedis:
    def __init__(self):
        self.data = {}

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.data:
            return False
        self.data[key] = value
        return True

    async def get(self, key):
        return self.data.get(key)

    async def eval(self, script, count, key, owner):
        if self.data.get(key) == owner:
            del self.data[key]
            return 1
        return 0

    async def aclose(self):
        pass


def context():
    return {"profile": {"userId": 1, "trainingExperience": "BEGINNER", "weeklyTrainingDays": 3,
                        "sessionDurationMinutes": 30, "availableTrainingTimes": "09:00",
                        "injuryOrMedicalNotes": "无", "averageSleepHours": 8},
            "body_measurement": {"heightCm": 175, "weightKg": 70}}


class Graph:
    async def astream(self, state, stream_mode):
        yield {"planner": {"planner": {"strategy": "test"},
                           "monthly_plan": [{"day": i, "sessions": [{"name": "walk"}]} for i in range(1, 31)]}}
        yield {"nutrition": {"nutrition_plan": [{"day": i, "meals": [{"name": name} for name in ("早餐", "午餐", "晚餐")]} for i in range(1, 31)]}}


class BackgroundTests(unittest.IsolatedAsyncioTestCase):
    async def test_task_diagnostic_context_is_propagated_and_reset(self):
        from app.diagnostics import task_id as diagnostic_task_id
        observed = []

        class ContextGraph:
            async def astream(self, state, stream_mode):
                observed.append(diagnostic_task_id.get())
                yield {"conversation": {"intent": "chat", "reply": "测试回复"}}

        previous = diagnostic_task_id.get()
        await execute_plan(1, "diagnostic-task", {"goal": "你好", "profile": {}}, graph=ContextGraph(), cache=self.cache)
        self.assertEqual(observed, ["diagnostic-task"])
        self.assertEqual(diagnostic_task_id.get(), previous)

    async def asyncSetUp(self):
        self.cache = RedisStateCache(client=MemoryRedis())

    async def test_submission_queues_authenticated_saved_plan(self):
        authenticated = context()
        authenticated["current_plan"] = {"startDate": "2026-10-21", "days": [{"day": 1}]}
        with patch.object(main, "state_cache", self.cache), patch.object(main, "authenticated_context", AsyncMock(return_value=authenticated)), patch.object(main, "enqueue_plan") as enqueue:
            await main.generate_monthly_plan(main.PlanRequest(goal="明天练什么"), "Bearer test")
        self.assertEqual(enqueue.call_args.args[2]["current_plan"], authenticated["current_plan"])

    async def test_submit_only_enqueues_and_is_idempotent(self):
        request = main.PlanRequest(goal="增肌", requestId=uuid4())
        with patch.object(main, "state_cache", self.cache), patch.object(main, "authenticated_context", AsyncMock(return_value=context())), patch.object(main, "enqueue_plan") as enqueue:
            first = await main.generate_monthly_plan(request, "Bearer test")
            second = await main.generate_monthly_plan(request, "Bearer test")
        self.assertEqual(first["taskId"], second["taskId"])
        self.assertEqual(enqueue.call_count, 1)
        self.assertEqual((await self.cache.get(1, first["taskId"]))["status"], "queued")

    async def test_worker_finishes_without_http_subscriber(self):
        state = {"goal": "增肌", "profile": context()["profile"]}
        await execute_plan(1, "task", state, graph=Graph(), cache=self.cache)
        snapshot = await self.cache.get(1, "task")
        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(len(snapshot["result"]["plan"]["days"]), 30)

    async def test_cross_user_query_is_denied(self):
        task_id = uuid4()
        await self.cache.save(2, str(task_id), {}, status="queued")
        with patch.object(main, "state_cache", self.cache), patch.object(main, "authenticated_context", AsyncMock(return_value=context())):
            with self.assertRaises(HTTPException) as error:
                await main.get_task_state(task_id, "Bearer test")
        self.assertEqual(error.exception.status_code, 404)

    async def test_reconnect_returns_completed_result(self):
        await self.cache.save(1, "task", {}, status="completed", result={"taskId": "task", "plan": {}})
        with patch.object(main, "state_cache", self.cache):
            events = [event async for event in main.task_events(1, "task")]
        self.assertIn("event: result", events[-1])

    async def test_invalid_final_document_marks_failure(self):
        class InvalidGraph:
            async def astream(self, state, stream_mode):
                yield {"planner": {"monthly_plan": []}}
        with self.assertLogs("app.worker", level="ERROR"):
            await execute_plan(1, "bad", {"goal": "test", "profile": {}}, graph=InvalidGraph(), cache=self.cache)
        self.assertEqual((await self.cache.get(1, "bad"))["status"], "failed")

    async def test_deadline_marks_failure(self):
        class SlowGraph:
            async def astream(self, state, stream_mode):
                await asyncio.sleep(10)
                yield {"planner": {}}
        with patch("app.worker.TASK_TIMEOUT", 0.01), self.assertLogs("app.worker", level="ERROR"):
            await execute_plan(1, "slow", {"goal": "test", "profile": {}}, graph=SlowGraph(), cache=self.cache)
        self.assertEqual((await self.cache.get(1, "slow"))["status"], "failed")

    async def test_active_execution_lock_prevents_duplicate_run(self):
        state = {"goal": "test", "profile": {}}
        await self.cache._client().set(self.cache.key(1, "locked") + ":execution-lock", "other")
        executed = await execute_plan(1, "locked", state, graph=Graph(), cache=self.cache)
        self.assertFalse(executed)

    async def test_http_submit_returns_202(self):
        import httpx
        with patch.object(main, "state_cache", self.cache), patch.object(main, "authenticated_context", AsyncMock(return_value=context())), patch.object(main, "enqueue_plan"):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test") as client:
                response = await client.post("/api/v1/plans/generate", json={"goal": "增肌"}, headers={"Authorization": "Bearer test"})
        self.assertEqual(response.status_code, 202)
        self.assertIn("taskId", response.json())

    async def test_chat_submission_keeps_history_without_body_requirements(self):
        import httpx
        with patch.object(main, "state_cache", self.cache), patch.object(main, "authenticated_context", AsyncMock(return_value={"profile": {"userId": 1}})), patch.object(main, "enqueue_plan") as enqueue:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test") as client:
                response = await client.post("/api/v1/assistant/messages", json={"goal": "继续", "messages": [{"role": "assistant", "content": "你想先了解哪种训练？"}]}, headers={"Authorization": "Bearer test"})
        self.assertEqual(response.status_code, 202)
        state = enqueue.call_args.args[2]
        self.assertEqual(state["conversation_history"][0]["role"], "assistant")
        self.assertEqual(state["body"], {})

    async def test_worker_returns_chat_without_plan_serialization(self):
        class ChatGraph:
            async def astream(self, state, stream_mode):
                yield {"conversation": {"intent": "chat", "reply": "你好，有什么想聊的？"}}
        await execute_plan(1, "chat", {"goal": "你好", "profile": {}}, graph=ChatGraph(), cache=self.cache)
        snapshot = await self.cache.get(1, "chat")
        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(snapshot["result"]["type"], "chat")
        self.assertNotIn("plan", snapshot["result"])


if __name__ == "__main__":
    unittest.main()
