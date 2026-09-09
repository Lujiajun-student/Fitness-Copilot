<template>
  <section class="plan-layout">
    <div>
      <div v-if="!dayPlan" class="hero-card">
        <div><span class="eyebrow lime">YOUR PLAN</span><h2>还没有可用计划</h2><p>前往私人助理，告诉 AI 你的目标，即可生成并自动覆盖这里的 30 天计划。</p></div>
        <button class="plan-cta" type="button" @click="$router.push('/assistant')">去生成计划</button>
      </div>
      <template v-else>
        <div class="hero-card">
          <div><span class="eyebrow lime">DAY {{ dayPlan.day }} · {{ dayPlan.training.type }}</span><h2>{{ selectedDateLabel }}</h2><p>{{ dayPlan.training.focus }} · {{ activePlan.value.goal }}</p></div>
          <div class="hero-ring"><b>{{ dayPlan.day }}</b><span>计划天数</span></div>
        </div>

        <section class="section-heading"><div><span class="eyebrow">TRAINING</span><h3>训练安排</h3></div><span class="tag">{{ dayPlan.training.exercises.length }} 个训练项目</span></section>
        <div class="schedule-card">
          <article v-for="(exercise, index) in dayPlan.training.exercises" :key="index" class="schedule-row">
            <time>{{ exercise.timeRange || "自由安排" }}</time><span class="timeline-dot"></span>
            <div><span class="tag">{{ exercise.category || dayPlan.training.type }}</span><h4>{{ exercise.name || exercise }}</h4><p>{{ exerciseDetail(exercise) }}</p></div><strong>{{ exercise.durationMinutes ? exercise.durationMinutes + " 分钟" : exercise.sets ? exercise.sets + " 组" : "" }}</strong>
          </article>
        </div>

        <section class="section-heading"><div><span class="eyebrow">NUTRITION</span><h3>当日三餐</h3></div><span class="tag">{{ dayPlan.nutrition.targetCalories || "—" }} kcal · 蛋白质 {{ dayPlan.nutrition.targetProteinG || "—" }} g</span></section>
        <div class="meal-grid"><article v-for="(meal, index) in dayPlan.nutrition.meals" :key="meal.name" class="meal-card"><span>{{ ["☀", "◒", "☾"][index] }}</span><small>{{ meal.name }}</small><h4>{{ meal.items[0] }}</h4><p>{{ meal.items.slice(1).join(" · ") }}</p></article></div>
      </template>
    </div>

    <aside class="calendar-card">
      <div class="calendar-header"><button type="button" @click="moveMonth(-1)">‹</button><strong>{{ monthLabel }}</strong><button type="button" @click="moveMonth(1)">›</button></div>
      <div class="calendar-weekdays"><span v-for="name in weekdayNames" :key="name">{{ name }}</span></div>
      <div class="calendar-grid"><button v-for="(cell, index) in calendarCells" :key="index" type="button" :disabled="!cell.day" :class="{ 'calendar-selected': cell.dateKey === selectedDateKey, 'calendar-planned': cell.day && hasPlan(cell.dateKey) }" @click="selectDate(cell.dateKey)">{{ cell.day || "" }}</button></div>
      <p class="calendar-note"><i></i> 有计划安排<br>点击日期查看当天训练与三餐</p>
    </aside>
  </section>
</template>

<script>
import { planApi } from "../api/fitness";
import { activePlan, setActivePlan } from "../api/plan-store";

function dateKey(year, month, day) { return year + "-" + String(month + 1).padStart(2, "0") + "-" + String(day).padStart(2, "0"); }
function parseDate(value) { var fields = value.split("-"); return new Date(Number(fields[0]), Number(fields[1]) - 1, Number(fields[2])); }

export default {
  data: function () {
    var today = new Date();
    return { activePlan: activePlan, calendarYear: today.getFullYear(), calendarMonth: today.getMonth(), selectedDateKey: dateKey(today.getFullYear(), today.getMonth(), today.getDate()), weekdayNames: ["日", "一", "二", "三", "四", "五", "六"] };
  },
  computed: {
    monthLabel: function () { return this.calendarYear + " 年 " + (this.calendarMonth + 1) + " 月"; },
    calendarCells: function () { var firstWeekday = new Date(this.calendarYear, this.calendarMonth, 1).getDay(); var days = new Date(this.calendarYear, this.calendarMonth + 1, 0).getDate(); var cells = []; for (var blank = 0; blank < firstWeekday; blank += 1) cells.push({ day: null }); for (var day = 1; day <= days; day += 1) cells.push({ day: day, dateKey: dateKey(this.calendarYear, this.calendarMonth, day) }); return cells; },
    selectedDateLabel: function () { var value = parseDate(this.selectedDateKey); return (value.getMonth() + 1) + " 月 " + value.getDate() + " 日"; },
    dayPlan: function () { var plan = this.activePlan.value; if (!plan || !plan.startDate || !plan.days) return null; var offset = Math.round((parseDate(this.selectedDateKey) - parseDate(plan.startDate)) / 86400000); return plan.days[offset] || null; }
  },
  created: function () { this.loadPlan(); },
  methods: {
    loadPlan: async function () { try { var saved = await planApi.latestMonthly(); if (saved && saved.content) setActivePlan(saved.content); } catch (error) { /* Local cache remains usable while the Java backend is offline. */ } },
    moveMonth: function (step) { var target = new Date(this.calendarYear, this.calendarMonth + step, 1); this.calendarYear = target.getFullYear(); this.calendarMonth = target.getMonth(); },
    selectDate: function (value) { if (value) this.selectedDateKey = value; },
    hasPlan: function (value) { var plan = this.activePlan.value; if (!plan || !plan.startDate) return false; var offset = Math.round((parseDate(value) - parseDate(plan.startDate)) / 86400000); return offset >= 0 && offset < plan.days.length; },
    exerciseDetail: function (exercise) { if (typeof exercise === "string") return "按计划完成并注意恢复"; var parts = []; if (exercise.reps) parts.push(exercise.reps + " 次"); if (exercise.restSeconds) parts.push("组间休息 " + exercise.restSeconds + " 秒"); if (exercise.notes) parts.push(exercise.notes); return parts.join(" · ") || "按计划完成并注意恢复"; }
  }
};
</script>
