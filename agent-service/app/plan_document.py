from datetime import date

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
    if state.get("intent") == "chat":
        return {"status": "replied", "type": "chat", "reply": state["reply"]}
    return {"status": "generated", "type": "plan", "reply": "已为你生成训练与饮食计划，训练建议一并附在计划中。", "profile": profile, "plan": build_plan_document(goal, state)}


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

