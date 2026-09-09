import json
from datetime import date

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.mcp_client import BackendMcpClient
from app.config import DeepSeekConfigurationError, get_settings
from app.workflow import plan_graph

app = FastAPI(title="Fitness Copilot Agent Service", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:8081", "http://127.0.0.1:8080", "http://127.0.0.1:8081"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class PlanRequest(BaseModel):
    goal: str = Field(..., min_length=1, description="User goal, such as fat loss")


def sse(event_type: str, payload: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def build_plan_document(goal: str, state: dict) -> dict:
    """Merge agent outputs into one day-centric document for storage and reuse."""
    nutrition_by_day = {item.get("day"): item for item in state["nutrition_plan"] if isinstance(item, dict)}
    days = []
    for training in state["monthly_plan"]:
        day_number = training.get("day")
        nutrition = nutrition_by_day.get(day_number)
        if not nutrition:
            raise RuntimeError(f"第 {day_number} 天缺少饮食计划，不能生成可用计划文档。")
        meals = nutrition.get("meals")
        if not isinstance(meals, list) or len(meals) != 3:
            raise RuntimeError(f"第 {day_number} 天必须包含早餐、午餐和晚餐。")
        days.append({
            "day": day_number,
            "status": "PENDING",
            "training": {
                "type": training.get("type"),
                "focus": training.get("focus"),
                "exercises": training.get("sessions", []),
            },
            "nutrition": {
                "targetCalories": nutrition.get("targetCalories"),
                "targetProteinG": nutrition.get("targetProteinG"),
                "meals": meals,
            },
        })
    if len(days) != 30:
        raise RuntimeError("计划文档必须包含完整 30 天。")
    return {
        "schemaVersion": "1.0",
        "goal": goal,
        "startDate": date.today().isoformat(),
        "summary": state["planner"],
        "safetyNotes": state.get("risks", []),
        "days": days,
    }


def build_generation_response(goal: str, profile: dict, state: dict) -> dict:
    return {"status": "generated", "profile": profile, "plan": build_plan_document(goal, state)}


def missing_safety_profile_fields(profile: dict) -> list[str]:
    fields = {
        "trainingExperience": "训练经验",
        "weeklyTrainingDays": "每周可训练天数",
        "sessionDurationMinutes": "单次可训练时长",
        "availableTrainingTimes": "可训练时段",
        "injuryOrMedicalNotes": "伤病或医疗限制（无也请明确填写“无”）",
        "averageSleepHours": "平均睡眠时长",
    }
    return [label for key, label in fields.items() if profile.get(key) in (None, "")]


@app.get("/api/health")
def health():
    settings = get_settings()
    return {"status": "ok", "service": "agent-service", "model": settings.deepseek_model, "deepseekConfigured": settings.deepseek_configured}


@app.post("/api/v1/plans/generate")
async def generate_monthly_plan(request: PlanRequest, authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少登录凭证")
    try:
        context = await BackendMcpClient().load_user_context(authorization[7:])
    except Exception as error:
        raise HTTPException(status_code=502, detail="无法通过 MCP 获取用户资料：" + str(error)) from error
    body = context["body_measurement"]
    if not body or not body.get("heightCm") or not body.get("weightKg"):
        raise HTTPException(status_code=422, detail="请先在个人信息页录入身高和体重")
    missing = missing_safety_profile_fields(context["profile"])
    if missing:
        raise HTTPException(status_code=422, detail="请先在个人信息页补充训练与健康档案：" + "、".join(missing))
    try:
        state = await plan_graph.ainvoke({"goal": request.goal, "body": body, "profile": context["profile"], "training_history": context.get("training_history", [])})
    except DeepSeekConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail="DeepSeek 生成计划失败：" + str(error)) from error
    return build_generation_response(request.goal, context["profile"], state)


@app.post("/api/v1/plans/generate/stream")
async def generate_monthly_plan_stream(request: PlanRequest, authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少登录凭证")

    async def events():
        try:
            yield sse("stage", {"stage": "profile", "message": "正在读取身体数据"})
            context = await BackendMcpClient().load_user_context(authorization[7:])
            body = context["body_measurement"]
            if not body or not body.get("heightCm") or not body.get("weightKg"):
                yield sse("error", {"detail": "请先在个人信息页录入身高和体重"})
                return
            missing = missing_safety_profile_fields(context["profile"])
            if missing:
                yield sse("error", {"detail": "请先在个人信息页补充训练与健康档案：" + "、".join(missing)})
                return

            state = {"goal": request.goal, "body": body, "profile": context["profile"], "training_history": context.get("training_history", [])}
            yield sse("stage", {"stage": "planner", "message": "正在规划 30 天训练框架"})
            strength_count = 0
            endurance_count = 0
            async for update in plan_graph.astream(state, stream_mode="updates"):
                for node, changes in update.items():
                    state.update(changes)
                    if node == "planner":
                        yield sse("stage", {"stage": "strength", "message": "正在规划无氧训练"})
                    elif node == "strength":
                        strength_count += 1
                        message = "正在规划有氧训练" if strength_count == 1 else "正在复核力量训练安排"
                        yield sse("stage", {"stage": "endurance", "message": message})
                    elif node == "endurance":
                        endurance_count += 1
                        message = "正在重新规划训练安排" if endurance_count == 1 else "正在进行训练安全审核"
                        yield sse("stage", {"stage": "revision" if endurance_count == 1 else "harness", "message": message})
                    elif node == "harness":
                        if changes.get("harness_approved"):
                            yield sse("stage", {"stage": "nutrition", "message": "安全审核通过，正在规划饮食计划"})
                        else:
                            yield sse("stage", {"stage": "revision", "message": "安全审核发现风险，正在重新规划整月训练"})
            result = build_generation_response(request.goal, context["profile"], state)
            yield sse("result", result)
        except DeepSeekConfigurationError as error:
            yield sse("error", {"detail": str(error)})
        except Exception as error:
            yield sse("error", {"detail": "AI 计划生成失败：" + str(error)})

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
