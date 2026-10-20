import unittest

from app.rag import retrieve_agent_knowledge
from app.workflow import build_graph


class LocalRag:
    async def retrieve(self, agent, query, limit=3):
        return retrieve_agent_knowledge(agent, query, limit)


class FakeModel:
    def __init__(self):
        self.retrieved_agents = []

    async def json_completion(self, prompt, payload):
        if "rag_knowledge" in payload:
            knowledge = payload["rag_knowledge"]
            assert knowledge["results"], "No retrieved context before model invocation"
            assert "knowledge_references" in prompt
            self.retrieved_agents.append(knowledge["agent"])
        if "健身总规划" in prompt:
            return {"monthly_plan": [{"day": day, "sessions": [{"name": "快走", "durationMinutes": 20}]} for day in range(1, 31)]}
        if "安全 Harness" in prompt:
            return {"approved": True, "risks": []}
        if "运动营养 Agent" in prompt:
            return {"nutrition_plan": [{"day": day, "meals": []} for day in range(1, 31)]}
        return {"revisions": []}


class WorkflowRetrievalTests(unittest.IsolatedAsyncioTestCase):
    async def test_each_specialist_receives_context_before_generation(self):
        model = FakeModel()
        graph = build_graph(model, LocalRag())
        result = await graph.ainvoke({"goal": "减脂", "body": {"heightCm": 175, "weightKg": 70},
                                     "profile": {"trainingExperience": "BEGINNER", "dietaryRestrictions": "乳糖不耐受"}})
        self.assertEqual(model.retrieved_agents, ["strength", "endurance", "strength", "endurance", "nutrition"])
        self.assertEqual(len(result["nutrition_plan"]), 30)


if __name__ == "__main__":
    unittest.main()
