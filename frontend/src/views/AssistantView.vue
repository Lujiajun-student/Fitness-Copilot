<template>
  <section class="assistant-layout">
    <div class="chat-card">
      <div class="assistant-welcome">
        <span class="assistant-orb">✦</span>
        <div><span class="eyebrow lime">FITNESS AI · DEEPSEEK</span><h2>你的私人训练助理</h2><p>告诉我目标，我会读取你的身体数据并生成经过安全审核的 30 天训练与三餐计划。</p></div>
      </div>
      <div class="messages" aria-live="polite">
        <div v-for="(message, index) in messages" :key="index" class="message" :class="message.role">{{ message.content }}</div>
        <div v-if="loading" class="message ai" style="max-width:100%">
          <b>{{ currentStageMessage }}</b>
          <div style="display:grid;gap:8px;margin-top:12px">
            <span v-for="stage in stages" v-if="stage.status !== 'pending'" :key="stage.id" :style="{ color: stage.status === 'active' ? '#587c1d' : '#6d756d' }">{{ stage.status === "done" ? "✓" : "●" }} {{ stage.label }}</span>
          </div>
        </div>
      </div>
      <div v-if="plan" style="border-top:1px solid var(--line);padding:20px 0">
        <div style="display:flex;gap:12px;align-items:center"><span class="eyebrow lime">AI 已生成</span><strong>30 天计划已就绪</strong></div>
        <p>{{ plan.plan.summary.strategy }}</p>
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin:12px 0;font-size:12px"><span>{{ plan.plan.days.length }} 天训练安排</span><span>{{ firstDay && firstDay.nutrition.meals.length }} 餐 / 日</span><span>{{ plan.plan.summary.estimated_calories || "—" }} kcal / 日</span></div>
        <div v-if="firstDay" style="display:grid;gap:7px;background:#f7f9f3;padding:13px;border-radius:9px;font-size:13px"><b>第 1 天 · {{ firstDay.training.focus }}</b><span v-for="(item, index) in firstDay.training.exercises" :key="index">{{ item.name || item }}</span></div>
      </div>
      <p v-if="error" class="form-error">{{ error }}</p>
      <form class="chat-input" @submit.prevent="send"><input v-model="draft" :disabled="loading" placeholder="例如：未来一个月减脂，每周训练 4 天" aria-label="输入给私人助理的目标"><button type="submit" :disabled="loading">{{ loading ? "生成中" : "生成计划" }}</button></form>
    </div>
    <aside class="assistant-context"><span class="eyebrow">真实服务状态</span><h3>计划生成器</h3><div class="metric"><span>模型</span><b>DeepSeek</b></div><div class="metric"><span>编排</span><b>LangGraph</b></div><div class="metric"><span>安全关卡</span><b>Harness 审核</b></div><p style="font-size:12px;margin:18px 0 0">生成前请先在个人信息页录入身高和体重。</p></aside>
  </section>
</template>

<script>
import { generatePlan } from "../api/agent";
import { planApi } from "../api/fitness";
import { setActivePlan } from "../api/plan-store";

export default {
  data: function () {
    return {
      draft: "", loading: false, error: "", plan: null, currentStageMessage: "正在准备生成计划",
      stages: [
        { id: "profile", label: "读取身体数据", status: "pending" },
        { id: "planner", label: "规划 30 天训练框架", status: "pending" },
        { id: "strength", label: "规划无氧训练", status: "pending" },
        { id: "endurance", label: "规划有氧训练", status: "pending" },
        { id: "revision", label: "重新规划训练安排", status: "pending" },
        { id: "harness", label: "训练安全审核", status: "pending" },
        { id: "nutrition", label: "规划饮食计划", status: "pending" }
      ],
      messages: [{ role: "ai", content: "你好。请告诉我你的训练目标，例如“未来一个月减脂，每周可以训练四天”。" }]
    };
  },
  computed: { firstDay: function () { return this.plan && this.plan.plan && this.plan.plan.days[0]; } },
  methods: {
    send: async function () {
      var goal = this.draft.trim();
      if (!goal || this.loading) return;
      this.error = "";
      this.messages.push({ role: "user", content: goal });
      this.draft = "";
      this.loading = true;
      this.currentStageMessage = "正在准备生成计划";
      this.stages.forEach(function (stage) { stage.status = "pending"; });
      try {
        var self = this;
        this.plan = await generatePlan(goal, function (event) { self.updateStage(event); });
        setActivePlan(this.plan.plan);
        try { await planApi.replaceMonthly(this.plan.plan); } catch (saveError) { this.error = "计划已生成，但暂未保存到服务器：" + saveError.message; }
        this.messages.push({ role: "ai", content: "计划已生成：包含 30 天训练和每日三餐。你可以在下方查看第 1 天预览。" });
        this.$router.push("/");
      } catch (error) {
        this.error = error.message;
        this.messages.push({ role: "ai", content: "暂时无法生成计划。请检查 Agent 服务、DeepSeek 密钥和身体数据后重试。" });
      } finally { this.loading = false; }
    },
    updateStage: function (event) {
      this.currentStageMessage = event.message;
      var activeIndex = this.stages.findIndex(function (stage) { return stage.id === event.stage; });
      if (activeIndex < 0) return;
      this.stages.forEach(function (stage, index) { stage.status = index < activeIndex ? "done" : index === activeIndex ? "active" : "pending"; });
    }
  }
};
</script>
