"""DeepSeek-powered LangGraph workflow with a strength/endurance debate loop."""

from copy import deepcopy
import asyncio
import json
import logging
import os
import re
from time import perf_counter
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.deepseek_client import DeepSeekClient, DeepSeekOutputTruncated
from app.assistant_context import calendar_context
from app.mcp_client import BackendMcpClient
from app.diagnostics import task_id, node_name
from app.prompts import RAG_INSTRUCTIONS
from app.prompts import CONVERSATION_PROMPT, ENDURANCE_PROMPT, HARNESS_PROMPT, NUTRITION_PROMPT, PLANNER_PROMPT, STRENGTH_PROMPT
from app.plan_document import missing_safety_profile_fields

logger = logging.getLogger(__name__)


class PlanState(TypedDict, total=False):
    goal: str
    body: dict[str, Any]
    profile: dict[str, Any]
    training_history: list[dict[str, Any]]
    conversation_history: list[dict[str, str]]
    current_plan: dict[str, Any] | None
    intent: str
    reply: str
    planner: dict[str, Any]
    strength_proposal: dict[str, Any]
    endurance_proposal: dict[str, Any]
    debate_round: int
    harness_feedback: dict[str, Any]
    risks: list[str]
    monthly_plan: list[dict[str, Any]]
    nutrition_plan: list[dict[str, Any]]
    knowledge_references: dict[str, list[str]]


def _context(state: PlanState) -> dict[str, Any]:
    return {
        "goal": state["goal"],
        "body_measurement": state.get("body", {}),
        "profile": {key: value for key, value in state.get("profile", {}).items() if key not in ("avatarDataUrl", "userId")},
        **calendar_context(state.get("current_plan")),
        "conversation_history": state.get("conversation_history", []),
        "training_history": state.get("training_history", []),
        "harness_feedback": state.get("harness_feedback", {}),
    }


def _apply_revisions(plan: list[dict[str, Any]], proposal: dict[str, Any]) -> list[dict[str, Any]]:
    result = deepcopy(plan)
    by_day = {item.get("day"): item for item in proposal.get("revisions", []) if isinstance(item, dict)}
    for item in result:
        revision = by_day.get(item.get("day"))
        if revision and isinstance(revision.get("sessions"), list):
            item["sessions"] = revision["sessions"]
    return result


def _start_minutes(profile: dict[str, Any]) -> int:
    """Use the first stated available time; retain 09:00 as an explicit fallback."""
    match = re.search(r"([01]?\d|2[0-3]):([0-5]\d)", str(profile.get("availableTrainingTimes") or ""))
    return int(match.group(1)) * 60 + int(match.group(2)) if match else 9 * 60


def _duration_minutes(session: dict[str, Any]) -> int:
    value = session.get("durationMinutes")
    if isinstance(value, (int, float)) and value > 0:
        return int(value)
    category = (str(session.get("category") or "") + " " + str(session.get("name") or "")).lower()
    sets = session.get("sets") if isinstance(session.get("sets"), (int, float)) else 0
    if "热身" in category or "warmup" in category or "拉伸" in category or "cooldown" in category:
        return 8
    if "有氧" in category or "cardio" in category or "快走" in category or "骑" in category:
        return 25
    if "恢复" in category or "休息" in category:
        return 20
    if "核心" in category or "core" in category:
        return max(8, int(sets) * 4)
    return max(10, int(sets) * 5) if sets else 12


def _time_label(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _schedule_plan(plan: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Make all exercise blocks sequential, rather than trusting repeated LLM time ranges."""
    scheduled = deepcopy(plan)
    for day in scheduled:
        cursor = _start_minutes(profile)
        normalized_sessions = []
        for raw_session in day.get("sessions", []):
            session = {"name": raw_session} if isinstance(raw_session, str) else raw_session
            duration = _duration_minutes(session)
            session["durationMinutes"] = duration
            session["timeRange"] = _time_label(cursor) + "–" + _time_label(cursor + duration)
            cursor += duration
            normalized_sessions.append(session)
        day["sessions"] = normalized_sessions
    return scheduled


def _validate_days(plan: list[dict[str, Any]]) -> list[str]:
    if len(plan) != 30 or any(not isinstance(day, dict) for day in plan):
        return ["训练计划必须覆盖完整 30 天。"]
    numbers = [day.get("day") for day in plan]
    if any(type(number) is not int for number in numbers) or numbers != list(range(1, 31)):
        return ["训练计划的 day 必须按顺序且不重复地覆盖 1 到 30。"]
    return []


def _validate_outline(plan: list[dict[str, Any]]) -> list[str]:
    errors = _validate_days(plan)
    if errors:
        return errors
    for day in plan:
        if day.get("type") not in ("strength", "cardio", "mixed", "recovery", "rest"):
            return [f"第 {day['day']} 天缺少有效训练类型。"]
        focus = day.get("focus")
        if not isinstance(focus, str) or not focus.strip() or len(focus.strip()) > 60:
            return [f"第 {day['day']} 天需要约30字、最长60字的简短训练概述。"]
    return []


def _validate_plan(plan: list[dict[str, Any]]) -> list[str]:
    errors = _validate_days(plan)
    if errors:
        return errors
    risks: list[str] = []
    for day in plan:
        if day.get("type") != "rest" and (not isinstance(day.get("sessions"), list) or not day["sessions"]):
            risks.append(f"第 {day.get('day', '?')} 天缺少具体训练安排。")
            break
    return risks


def build_graph(client: DeepSeekClient | None = None, retriever=None):
    llm = client or DeepSeekClient()
    rag = retriever if retriever is not None else BackendMcpClient()

    def tracked_node(name, function):
        async def run(state):
            token = node_name.set(name)
            started = perf_counter()
            logger.info("node_started task=%s node=%s debate_round=%s", task_id.get(), name, state.get("debate_round", 0))
            try:
                output = await function(state)
                logger.info("node_completed task=%s node=%s elapsed_ms=%d day_count=%s", task_id.get(), name,
                            (perf_counter() - started) * 1000, len(output.get("monthly_plan", output.get("nutrition_plan", []))))
                return output
            except Exception as error:
                logger.error("node_failed task=%s node=%s elapsed_ms=%d error_type=%s", task_id.get(), name,
                             (perf_counter() - started) * 1000, type(error).__name__)
                raise
            finally:
                node_name.reset(token)
        return run

    async def specialist_completion(agent, prompt, payload):
        # Never include tokens, account identifiers or the full saved plan in a search query.
        topics = {"strength": "力量 动作 训练负荷 恢复", "endurance": "有氧 心肺 低冲击 恢复", "nutrition": "三餐 蛋白质 饮食限制 食物过敏"}
        profile = payload.get("profile", {})
        query = json.dumps({"goal": payload["goal"], "topics": topics[agent],
                            "body": payload.get("body_measurement", {}),
                            "constraints": {key: profile.get(key) for key in ("trainingExperience", "injuryOrMedicalNotes", "availableEquipment", "dietaryRestrictions")}}, ensure_ascii=False)
        try:
            timeout = max(1, float(os.getenv("RAG_RERANK_TIMEOUT_SECONDS", "120"))) + 30
            knowledge = await asyncio.wait_for(rag.retrieve(agent, query, limit=10), timeout=timeout)
            if not isinstance(knowledge, dict) or knowledge.get("agent") != agent or not isinstance(knowledge.get("results"), list):
                raise ValueError("Invalid retrieval response")
            if any(not isinstance(item, dict) or item.get("knowledgeBase") != agent
                   or not isinstance(item.get("id"), str) or not item["id"].startswith(agent + "/")
                   for item in knowledge["results"]):
                raise ValueError("Cross-role retrieval response")
            knowledge = {**knowledge, "status": "ok"}
            logger.info("rag_completed task=%s node=%s result_count=%s reranker=%s", task_id.get(), agent,
                        len(knowledge["results"]), knowledge.get("reranker", "unknown"))
        except Exception:
            logging.getLogger(__name__).warning("RAG retrieval unavailable for %s; using model-only generation", agent)
            knowledge = {"agent": agent, "status": "unavailable", "results": []}
        # Retrieve once per node/role, then generate bounded date windows. Full-month
        # action/meal JSON easily exceeds the provider's per-response output limit.
        plan = payload["monthly_plan"]
        outline = [{key: day[key] for key in ("day", "type", "focus")} for day in plan]
        semaphore = asyncio.Semaphore(2)
        result_key = "nutrition_plan" if agent == "nutrition" else "revisions"

        async def complete_batch(days):
            numbers = [day["day"] for day in days]
            batch_payload = {**payload, "monthly_plan": days, "calendar_outline": outline,
                             "target_days": numbers, "rag_knowledge": knowledge}
            for key in ("required_days", "pending_days"):
                if key in batch_payload:
                    batch_payload[key] = [number for number in payload[key] if number in numbers]
            logger.info("batch_started task=%s node=%s days=%s", task_id.get(), agent, numbers)
            try:
                async with semaphore:
                    output = await llm.json_completion(prompt + RAG_INSTRUCTIONS, batch_payload)
            except DeepSeekOutputTruncated:
                if len(days) == 1:
                    logger.error("batch_single_day_truncated task=%s node=%s day=%s", task_id.get(), agent, numbers[0])
                    raise
                midpoint = len(days) // 2
                logger.warning("batch_split task=%s node=%s days=%s reason=output_truncated", task_id.get(), agent, numbers)
                # Discard the partial response; regenerate only this window in smaller parts.
                return await complete_batch(days[:midpoint]) + await complete_batch(days[midpoint:])
            items = output.get(result_key, [] if agent != "nutrition" else None)
            if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
                raise RuntimeError(f"{agent} 分批输出缺少有效的 {result_key}。")
            returned = [item.get("day") for item in items]
            if any(type(number) is not int or number not in numbers for number in returned) or len(set(returned)) != len(returned):
                raise RuntimeError(f"{agent} 分批输出包含重复或超出本批范围的日期。")
            if agent == "nutrition":
                if set(returned) != set(numbers) or any(not isinstance(item.get("meals"), list) or len(item["meals"]) != 3 for item in items):
                    raise RuntimeError("饮食 Agent 分批输出未覆盖目标日期或缺少三餐。")
            elif any(not isinstance(item.get("sessions"), list) or any(not isinstance(session, dict) for session in item["sessions"]) for item in items):
                raise RuntimeError(f"{agent} 分批输出的动作明细格式无效。")
            logger.info("batch_completed task=%s node=%s days=%s item_count=%s", task_id.get(), agent, numbers, len(items))
            return [output]

        tasks = [asyncio.create_task(complete_batch(plan[index:index + 5])) for index in range(0, len(plan), 5)]
        try:
            batches = await asyncio.gather(*tasks)
        except BaseException:
            # A failed/cancelled node must not leave paid model requests running.
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        parts = [part for batch in batches for part in batch]
        output = {result_key: sorted([item for part in parts for item in part.get(result_key, [])], key=lambda item: item["day"])}
        for key in ("recommendations", "concerns", "knowledge_references"):
            output[key] = list(dict.fromkeys(item for part in parts for item in part.get(key, []) if isinstance(item, str)))
        for key in ("estimated_calories", "daily_protein_g"):
            values = [part[key] for part in parts if type(part.get(key)) in (int, float)]
            if values:
                output[key] = round(sum(values) / len(values), 1)
        allowed = {item["id"] for item in knowledge["results"] if isinstance(item, dict) and isinstance(item.get("id"), str)}
        references = output.get("knowledge_references", [])
        output["knowledge_references"] = list(dict.fromkeys(item for item in references if isinstance(item, str) and item in allowed)) if isinstance(references, list) else []
        return output

    async def conversation_node(state: PlanState) -> PlanState:
        output = await llm.json_completion(CONVERSATION_PROMPT, _context(state))
        if output.get("intent") != "plan":
            return {"intent": "chat", "reply": str(output.get("reply") or "你想聊聊训练和饮食，还是让我帮你制定一份计划？")}
        body = state.get("body") or {}
        missing = missing_safety_profile_fields(state.get("profile", {}))
        if not body.get("heightCm") or not body.get("weightKg"):
            missing = ["身高和体重"] + missing
        if missing:
            return {"intent": "chat", "reply": "可以帮你制定计划。请先在个人信息中补充" + "、".join(missing) + "，保存后告诉我继续生成即可。也可以先和我聊聊你的目标。"}
        return {"intent": "plan", "goal": str(output.get("plan_goal") or state["goal"])[:2000]}

    async def planner_node(state: PlanState) -> PlanState:
        output = await llm.json_completion(PLANNER_PROMPT, _context(state))
        plan = output.get("monthly_plan")
        if not isinstance(plan, list):
            raise RuntimeError("总规划 Agent 未返回 monthly_plan。")
        errors = _validate_outline(plan)
        if errors:
            raise RuntimeError("计划数据格式不完整：" + "；".join(errors))
        outline = [{"day": day["day"], "type": day["type"], "focus": day["focus"].strip(), "sessions": []} for day in plan]
        logger.info("planner_outline_validated task=%s node=planner day_count=%s max_focus_chars=%s", task_id.get(),
                    len(outline), max(len(day["focus"]) for day in outline))
        return {"planner": {"strategy": output.get("strategy", "循序渐进、恢复优先")}, "monthly_plan": outline, "debate_round": 0}

    async def strength_node(state: PlanState) -> PlanState:
        required_days = [day["day"] for day in state["monthly_plan"] if day.get("type") in ("strength", "mixed") and not day.get("sessions")]
        payload = {**_context(state), "monthly_plan": state["monthly_plan"], "previous_endurance_feedback": state.get("endurance_proposal", {}),
                   "phase": "detail" if state.get("debate_round", 0) == 0 else "review", "required_days": required_days}
        output = await specialist_completion("strength", STRENGTH_PROMPT, payload)
        output["knowledge_references"] = list(dict.fromkeys(state.get("strength_proposal", {}).get("knowledge_references", []) + output["knowledge_references"]))
        plan = _schedule_plan(_apply_revisions(state["monthly_plan"], output), state.get("profile", {}))
        missing = [day["day"] for day in plan if day.get("type") in ("strength", "mixed") and not day.get("sessions")]
        if missing:
            raise RuntimeError("力量 Agent 未补齐训练日动作：" + ",".join(map(str, missing)))
        return {"strength_proposal": output, "monthly_plan": plan}

    async def endurance_node(state: PlanState) -> PlanState:
        pending_days = [day["day"] for day in state["monthly_plan"] if day.get("type") != "rest" and not day.get("sessions")]
        payload = {**_context(state), "monthly_plan": state["monthly_plan"], "strength_feedback": state.get("strength_proposal", {}),
                   "phase": "detail" if state.get("debate_round", 0) == 0 else "review", "pending_days": pending_days}
        output = await specialist_completion("endurance", ENDURANCE_PROMPT, payload)
        output["knowledge_references"] = list(dict.fromkeys(state.get("endurance_proposal", {}).get("knowledge_references", []) + output["knowledge_references"]))
        plan = _schedule_plan(_apply_revisions(state["monthly_plan"], output), state.get("profile", {}))
        errors = _validate_plan(plan)
        if errors:
            raise RuntimeError("专业 Agent 动作明细不完整：" + "；".join(errors))
        return {"endurance_proposal": output, "monthly_plan": plan, "debate_round": state.get("debate_round", 0) + 1}

    async def harness_node(state: PlanState) -> PlanState:
        try:
            output = await llm.json_completion(HARNESS_PROMPT, {**_context(state), "monthly_plan": state["monthly_plan"], "strength_feedback": state.get("strength_proposal", {}), "endurance_feedback": state.get("endurance_proposal", {})})
            raw = output.get("suggestions", output.get("risks", []))
            suggestions = [item for item in raw if isinstance(item, str)] if isinstance(raw, list) else []
        except Exception as error:
            logger.warning("harness_advice_unavailable task=%s node=harness error_type=%s", task_id.get(), type(error).__name__)
            suggestions = ["本次未能生成个性化训练建议；请结合自身恢复情况调整训练，出现不适时停止。"]
        return {"risks": suggestions, "harness_feedback": {"mode": "advisory", "suggestions": suggestions}}

    async def nutrition_node(state: PlanState) -> PlanState:
        output = await specialist_completion("nutrition", NUTRITION_PROMPT, {**_context(state), "monthly_plan": state["monthly_plan"]})
        nutrition_plan = output.get("nutrition_plan")
        if not isinstance(nutrition_plan, list) or len(nutrition_plan) != 30:
            raise RuntimeError("饮食 Agent 未返回完整 30 天饮食计划。")
        references = {"strength": state.get("strength_proposal", {}).get("knowledge_references", []),
                      "endurance": state.get("endurance_proposal", {}).get("knowledge_references", []),
                      "nutrition": output["knowledge_references"]}
        return {"nutrition_plan": nutrition_plan, "knowledge_references": references, "planner": {**state["planner"], "knowledge_references": references, "estimated_calories": output.get("estimated_calories"), "daily_protein_g": output.get("daily_protein_g")}}

    def debate_route(state: PlanState) -> str:
        return "strength" if state.get("debate_round", 0) < 2 else "harness"

    graph = StateGraph(PlanState)
    for name, function in (("conversation", conversation_node), ("planner", planner_node), ("strength", strength_node),
                           ("endurance", endurance_node), ("harness", harness_node), ("nutrition", nutrition_node)):
        graph.add_node(name, tracked_node(name, function))
    graph.add_edge(START, "conversation")
    graph.add_conditional_edges("conversation", lambda state: "planner" if state.get("intent") == "plan" else "end", {"planner": "planner", "end": END})
    graph.add_edge("planner", "strength")
    graph.add_edge("strength", "endurance")
    graph.add_conditional_edges("endurance", debate_route, {"strength": "strength", "harness": "harness"})
    graph.add_edge("harness", "nutrition")
    graph.add_edge("nutrition", END)
    return graph.compile()


plan_graph = build_graph()
