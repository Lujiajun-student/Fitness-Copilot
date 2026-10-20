import json
import unittest

from app.state_cache import RedisStateCache, StateCacheError, cached_updates


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    async def set(self, key, value, ex):
        self.values[key] = value
        self.ttls[key] = ex

    async def get(self, key):
        return self.values.get(key)


class Graph:
    async def astream(self, state, stream_mode):
        yield {"planner": {"monthly_plan": [{"day": 1}]}}
        yield {"harness": {"harness_approved": True}}


class BrokenGraph:
    async def astream(self, state, stream_mode):
        yield {"planner": {"debate_round": 0}}
        raise RuntimeError("model failed")


class StateCacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_user_and_task_isolation_and_ttl(self):
        redis = FakeRedis()
        cache = RedisStateCache(client=redis, ttl=60)
        await cache.save(1, "a", {"goal": "增肌"})
        await cache.save(2, "a", {"goal": "减脂"})
        await cache.save(1, "b", {"goal": "体能"})
        self.assertEqual((await cache.get(1, "a"))["state"]["goal"], "增肌")
        self.assertEqual((await cache.get(2, "a"))["state"]["goal"], "减脂")
        self.assertIsNone(await cache.get(3, "a"))
        self.assertEqual(set(redis.ttls.values()), {60})

    async def test_updates_are_cached_and_merged(self):
        cache = RedisStateCache(client=FakeRedis())
        state = {"goal": "增肌"}
        async for _ in cached_updates(Graph(), state, cache, 1, "task"):
            pass
        snapshot = await cache.get(1, "task")
        self.assertEqual(snapshot["node"], "harness")
        self.assertTrue(snapshot["state"]["harness_approved"])
        self.assertIn("monthly_plan", snapshot["state"])

    async def test_failure_retains_last_state(self):
        cache = RedisStateCache(client=FakeRedis())
        with self.assertRaises(RuntimeError):
            async for _ in cached_updates(BrokenGraph(), {}, cache, 1, "task"):
                pass
        snapshot = await cache.get(1, "task")
        self.assertEqual(snapshot["status"], "failed")
        self.assertEqual(snapshot["state"]["debate_round"], 0)

    async def test_disabled_cache_does_not_connect(self):
        cache = RedisStateCache(url="")
        await cache.save(1, "task", {})
        self.assertIsNone(await cache.get(1, "task"))


if __name__ == "__main__":
    unittest.main()
