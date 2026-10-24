import asyncio
import json
from uuid import UUID, uuid4
from typing import Literal

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from redis.exceptions import RedisError

from app.config import get_settings
from app.mcp_client import BackendMcpClient
from app.mcp_server import backend_get
from app.plan_document import build_plan_document, build_generation_response, missing_safety_profile_fields
from app.state_cache import RedisStateCache, StateCacheError
from app.task_queue import enqueue_plan

app = FastAPI(title="Fitness Copilot Agent Service", version="0.2.0")
app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:8081", "http://127.0.0.1:8080", "http://127.0.0.1:8081"],
    allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])
state_cache = RedisStateCache()


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=3000)


class PlanRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=2000)
    requestId: UUID | None = None
    messages: list[ConversationMessage] = Field(default_factory=list, max_length=20)


def sse(event_type, payload):
    return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def authenticated_context(authorization, profile_only=False):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "缺少登录凭证")
    try:
        if profile_only:
            return {"profile": await backend_get("/api/users/me", authorization[7:])}
        return await BackendMcpClient().load_user_context(authorization[7:])
    except httpx.HTTPStatusError as error:
        raise HTTPException(401 if error.response.status_code == 401 else 502, "登录已失效或用户资料暂不可用") from error
    except Exception as error:
        raise HTTPException(502, "无法读取用户资料，请检查 Java 后端") from error


@app.exception_handler(StateCacheError)
@app.exception_handler(RedisError)
async def cache_error_handler(request, error):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=503, content={"detail": "后台任务存储不可用，请启动 Redis 并配置 REDIS_URL"})


@app.get("/api/health")
def health():
    settings = get_settings()
    return {"status": "ok", "service": "agent-service", "model": settings.deepseek_model,
            "deepseekConfigured": settings.deepseek_configured, "backgroundTasksConfigured": state_cache.enabled}


@app.post("/api/v1/plans/generate", status_code=202)
@app.post("/api/v1/assistant/messages", status_code=202)
async def generate_monthly_plan(request: PlanRequest, authorization: str | None = Header(default=None)):
    context = await authenticated_context(authorization)
    if not state_cache.enabled:
        raise HTTPException(503, "请先启动 Redis，并在 .env 中配置 REDIS_URL；计划生成需要后台 Worker")
    body = context.get("body_measurement") or {}
    user_id = context["profile"]["userId"]
    task_id = str(request.requestId or uuid4())
    lock = state_cache.key(user_id, task_id) + ":submit-lock"
    owner = str(uuid4())
    acquired = await state_cache._client().set(lock, owner, nx=True, ex=30)
    if not acquired:
        raise HTTPException(409, "同一任务正在提交，请稍后重试")
    try:
        existing = await state_cache.get(user_id, task_id)
        if existing:
            if existing["state"].get("goal") != request.goal:
                raise HTTPException(409, "任务 ID 已用于另一个目标")
            return {"taskId": task_id, "status": existing["status"]}
        state = {"goal": request.goal, "body": body, "profile": context["profile"], "training_history": context.get("training_history", []),
                 "current_plan": context.get("current_plan"),
                 "conversation_history": [message.model_dump() for message in request.messages]}
        await state_cache.save(user_id, task_id, state, status="queued")
        try:
            await asyncio.to_thread(enqueue_plan, user_id, task_id, state)
        except Exception as error:
            await state_cache._client().delete(state_cache.key(user_id, task_id))
            raise HTTPException(503, "后台队列不可用，请检查 Redis 和 Worker") from error
        return {"taskId": task_id, "status": "queued"}
    finally:
        await state_cache._client().eval("if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end", 1, lock, owner)


async def owned_snapshot(task_id, authorization):
    context = await authenticated_context(authorization, profile_only=True)
    snapshot = await state_cache.get(context["profile"]["userId"], str(task_id))
    if not snapshot:
        raise HTTPException(404, "任务不存在或已过期，请重新生成")
    return snapshot


def task_progress(snapshot):
    node = snapshot.get("node")
    next_stage = {
        None: ("conversation", "正在思考回复"),
        "conversation": ("planner", "正在规划训练框架"),
        "planner": ("strength", "正在规划无氧训练"),
        "strength": ("endurance", "正在规划有氧训练"),
        "nutrition": ("nutrition", "正在整理计划结果"),
    }
    if node == "conversation" and snapshot["state"].get("intent") == "chat":
        stage, message = ("conversation", "回复已准备好")
    elif node == "endurance":
        stage, message = ("revision", "正在完善训练安排") if snapshot["state"].get("debate_round", 0) < 2 else ("harness", "正在整理训练建议")
    elif node == "harness":
        stage, message = ("nutrition", "正在规划饮食计划")
    else:
        stage, message = next_stage.get(node, ("planner", "正在规划训练框架"))
    return {"taskId": snapshot["taskId"], "status": snapshot["status"], "stage": stage,
            "message": message, "updatedAt": snapshot["updatedAt"], "result": snapshot.get("result"), "error": snapshot.get("error")}


@app.get("/api/v1/plans/tasks/{task_id}/state")
async def get_task_state(task_id: UUID, authorization: str | None = Header(default=None)):
    return await owned_snapshot(task_id, authorization)


@app.get("/api/v1/plans/tasks/{task_id}")
async def get_task(task_id: UUID, authorization: str | None = Header(default=None)):
    return task_progress(await owned_snapshot(task_id, authorization))


async def task_events(user_id, task_id):
    while True:
        snapshot = await state_cache.get(user_id, task_id)
        if not snapshot:
            yield sse("error", {"detail": "任务不存在或已过期"})
            return
        if snapshot["status"] == "completed":
            yield sse("result", snapshot["result"])
            return
        if snapshot["status"] == "failed":
            yield sse("error", {"detail": snapshot.get("error")})
            return
        yield sse("stage", task_progress(snapshot))
        await asyncio.sleep(3)


@app.get("/api/v1/plans/tasks/{task_id}/events")
async def subscribe_task(task_id: UUID, authorization: str | None = Header(default=None)):
    snapshot = await owned_snapshot(task_id, authorization)
    return StreamingResponse(task_events(snapshot["userId"], str(task_id)), media_type="text/event-stream")


@app.post("/api/v1/plans/generate/stream")
async def generate_monthly_plan_stream(request: PlanRequest, authorization: str | None = Header(default=None)):
    submitted = await generate_monthly_plan(request, authorization)
    return await subscribe_task(UUID(submitted["taskId"]), authorization)
