<template>
  <section class="assistant-layout">
    <div class="chat-card">
      <div class="conversation-toolbar">
        <div class="conversation-tabs" role="tablist" aria-label="助理会话">
          <div v-for="item in conversations" :key="item.id" class="conversation-tab" :class="{ active: item.id === activeConversationId }">
            <button :id="'conversation-tab-' + item.id" type="button" role="tab" class="conversation-select" :aria-selected="item.id === activeConversationId ? 'true' : 'false'" :aria-controls="'conversation-panel-' + item.id" :tabindex="item.id === activeConversationId ? 0 : -1" :title="item.title" @click="select(item.id)" @keydown.left.prevent="moveTab(-1)" @keydown.right.prevent="moveTab(1)">
              <span v-if="item.task" class="conversation-busy" aria-label="正在处理"></span><span class="conversation-title">{{ item.title }}</span>
            </button>
            <button type="button" class="conversation-delete" :aria-label="'删除会话：' + item.title" :title="'删除会话：' + item.title" @click.stop="remove(item)">×</button>
          </div>
        </div>
        <button type="button" class="conversation-new" @click="newConversation"><span aria-hidden="true">＋</span> 新会话</button>
      </div>
      <p v-if="persistenceError" class="form-error" role="alert">{{ persistenceError }}</p>
      <div :id="'conversation-panel-' + activeConversationId" class="conversation-panel" role="tabpanel" :aria-labelledby="'conversation-tab-' + activeConversationId">
      <div class="assistant-welcome">
        <span class="assistant-orb">✦</span>
        <div><span class="eyebrow lime">FITNESS COPILOT</span><h2>你的私人助理</h2><p>聊聊训练与饮食，或告诉我目标，一起制定适合你的计划。</p></div>
      </div>
      <div ref="messages" class="messages" aria-live="polite" :aria-busy="loading ? 'true' : 'false'">
        <div v-for="(message, index) in messages" :key="index" class="message" :class="message.role">{{ message.content }}</div>
        <div v-if="loading" class="message ai" style="max-width:100%">
          <b>{{ currentStageMessage }}</b>
          <div v-if="!isChatting" style="display:grid;gap:8px;margin-top:12px">
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
      <form class="chat-input" @submit.prevent="send"><input ref="draft" v-model="draft" :disabled="loading" maxlength="2000" placeholder="聊一聊，或说：帮我制定未来一个月的训练计划" aria-label="给私人助理发消息"><button type="submit" :disabled="loading || !draft.trim()">{{ loading ? "处理中" : "发送" }}</button></form>
      </div>
    </div>
    <aside class="assistant-context"><span class="eyebrow">与你一起行动</span><h3>可以这样开始</h3><div class="metric"><span>日常咨询</span><b>深蹲时怎样保持动作稳定？</b></div><div class="metric"><span>聊聊近况</span><b>最近训练后有些疲劳</b></div><div class="metric"><span>制定计划</span><b>帮我安排未来一个月的训练和三餐</b></div><p style="font-size:12px;margin:18px 0 0">会话按账号保存在当前浏览器，点击上方标签可继续旧对话。切换会话不影响后台任务；删除会话不会删除已保存的训练计划。</p></aside>
  </section>
</template>

<script>
import { generation, startGeneration, saveDraft, createConversation, selectConversation, deleteConversation } from "../api/generation-store";

export default {
  computed: {
    conversations: function () { return generation.conversations; },
    activeConversationId: function () { return generation.activeConversationId; },
    persistenceError: function () { return generation.persistenceError; },
    draft: { get: function () { return generation.draft; }, set: function (value) { saveDraft(value); } },
    loading: function () { return Boolean(generation.task); },
    isChatting: function () { return generation.stage === "conversation"; },
    error: function () { return generation.error; },
    plan: function () { return generation.plan; },
    messages: function () { return generation.messages; },
    currentStageMessage: function () { return generation.currentStageMessage; },
    firstDay: function () { return this.plan && this.plan.plan && this.plan.plan.days[0]; },
    stages: function () {
      var definitions = [
        ["profile", "读取身体数据"], ["planner", "规划 30 天训练框架"],
        ["strength", "规划无氧训练"], ["endurance", "规划有氧训练"],
        ["revision", "完善训练安排"], ["harness", "整理训练建议"], ["nutrition", "规划饮食计划"]
      ];
      var activeIndex = definitions.findIndex(function (stage) { return stage[0] === generation.stage; });
      return definitions.map(function (stage, index) {
        return { id: stage[0], label: stage[1], status: index < activeIndex ? "done" : index === activeIndex ? "active" : "pending" };
      });
    }
  },
  watch: {
    activeConversationId: function () {
      this.scrollMessages();
      this.$nextTick(function () {
        var tab = document.getElementById("conversation-tab-" + this.activeConversationId);
        if (tab) tab.scrollIntoView({ block: "nearest", inline: "nearest" });
      });
    },
    "messages.length": function () { this.scrollMessages(); }
  },
  mounted: function () { this.scrollMessages(); },
  methods: {
    send: function () { startGeneration(); },
    select: function (id) { selectConversation(id); },
    newConversation: function () { createConversation(); this.$nextTick(function () { this.$refs.draft.focus(); }); },
    remove: function (item) {
      var hasHistory = item.messages.some(function (message) { return message.role === "user"; });
      var warning = item.task ? "该会话仍有后台任务。删除后将不再接收其结果，但已提交的后台任务不会被取消。" : "删除后无法恢复此会话的聊天记录和草稿。";
      if ((hasHistory || item.task || item.draft.trim()) && !window.confirm("删除“" + item.title + "”？\n" + warning + "\n已保存的训练计划不会被删除。")) return;
      deleteConversation(item.id);
    },
    moveTab: function (offset) {
      var index = this.conversations.findIndex(function (item) { return item.id === generation.activeConversationId; });
      var next = this.conversations[(index + offset + this.conversations.length) % this.conversations.length];
      if (!next) return;
      selectConversation(next.id);
      this.$nextTick(function () { document.getElementById("conversation-tab-" + next.id).focus(); });
    },
    scrollMessages: function () { this.$nextTick(function () { if (this.$refs.messages) this.$refs.messages.scrollTop = this.$refs.messages.scrollHeight; }); }
  }
};
</script>
