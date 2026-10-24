import tempfile
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app import rag


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        patcher = patch.dict(os.environ, {"RAG_INDEX_PATH": str(Path(directory.name) / "absent.sqlite3")})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_nutrition_retrieves_dietary_restrictions(self):
        result = rag.retrieve_agent_knowledge("nutrition", "乳糖不耐受 食物过敏 三餐 蛋白质")
        self.assertTrue(result["results"])
        self.assertTrue(any("乳糖不耐受" in d["content"] for d in result["results"]))
        self.assertTrue(all(d["knowledgeBase"] in rag.AGENT_SCOPES["nutrition"] for d in result["results"]))

    def test_roles_cannot_retrieve_other_roles_or_old_shared_folders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for scope in ("strength", "endurance", "nutrition", "sports_training", "human_science", "sports_nutrition"):
                (root / scope).mkdir()
                (root / scope / "guide.md").write_text("# 隔离测试\n\n统一检索标记 " + scope, encoding="utf-8")
            with patch.object(rag, "KNOWLEDGE_ROOT", root):
                for agent in ("strength", "endurance", "nutrition"):
                    result = rag.retrieve_agent_knowledge(agent, "统一检索标记", limit=5)
                    self.assertTrue(result["results"])
                    self.assertEqual({item["knowledgeBase"] for item in result["results"]}, {agent})
                    self.assertTrue(all(item["id"].startswith(agent + "/") for item in result["results"]))

    def test_no_match_and_invalid_agent(self):
        self.assertEqual(rag.retrieve_agent_knowledge("nutrition", "zzzznotfound")["results"], [])
        with self.assertRaises(ValueError):
            rag.retrieve_agent_knowledge("../../strength", "训练")
        with self.assertRaises(ValueError):
            rag.retrieve_agent_knowledge("planner", "训练")

    def test_late_section_is_retrieved_without_prefix_truncation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "strength").mkdir()
            (root / "strength" / "long.md").write_text("# 文档\n\n## 起始\n\n" + "无关内容" * 500 + "\n\n## 目标\n\n独特哑铃调整建议", encoding="utf-8")
            with patch.object(rag, "KNOWLEDGE_ROOT", root):
                result = rag.retrieve_agent_knowledge("strength", "独特哑铃")
            self.assertIn("独特哑铃", result["results"][0]["content"])
            self.assertLessEqual(len(result["results"][0]["content"]), 1000)


if __name__ == "__main__":
    unittest.main()
