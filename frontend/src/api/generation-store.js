import Vue from "vue";
import { session } from "./session";
import { submitPlan, getPlanTask } from "./agent";
import { planApi } from "./fitness";
import { setActivePlan, restoreActivePlan } from "./plan-store";

function empty() {
  return { draft: "", task: null, plan: null, error: "", currentStageMessage: "", stage: "profile",
    messages: [{ role: "ai", content: "你好！可以和我聊聊训练、饮食或你的近况，也可以让我为你制定一份计划。" }] };
}
var fields = Object.keys(empty());
export var generation = Vue.observable(Object.assign(empty(), { conversations: [], activeConversationId: null, persistenceError: "" }));
var userId = null;
var epoch = 0;
var timers = {};
var inFlight = {};
function key() { return "fitness-copilot-generation-" + userId; }
function find(id) { return generation.conversations.find(function (item) { return item.id === id; }); }
function active() { return find(generation.activeConversationId); }
function syncActive() {
  var current = active() || empty();
  fields.forEach(function (field) { generation[field] = current[field]; });
}
function persist() {
  if (!userId) return;
  try {
    window.localStorage.setItem(key(), JSON.stringify({ version: 2, activeConversationId: generation.activeConversationId, conversations: generation.conversations }));
    generation.persistenceError = "";
  } catch (error) {
    generation.persistenceError = "浏览器存储空间不足或不可用，会话暂时无法保存，请勿刷新页面。";
  }
}
function publish() { syncActive(); persist(); }
function uuid() {
  var bytes = new Uint8Array(16); window.crypto.getRandomValues(bytes);
  bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
  var hex = Array.from(bytes, function (n) { return n.toString(16).padStart(2, "0"); }).join("");
  return hex.slice(0, 8) + "-" + hex.slice(8, 12) + "-" + hex.slice(12, 16) + "-" + hex.slice(16, 20) + "-" + hex.slice(20);
}
function titleFor(text) { return Array.from(text.replace(/\s+/g, " ").trim()).slice(0, 18).join("") || "新会话"; }
function conversation(saved) {
  var item = Object.assign(empty(), { id: uuid(), title: "新会话", createdAt: Date.now() });
  if (saved && typeof saved === "object") {
    fields.forEach(function (field) { if (Object.prototype.hasOwnProperty.call(saved, field)) item[field] = saved[field]; });
    item.id = typeof saved.id === "string" && /^[a-zA-Z0-9-]+$/.test(saved.id) ? saved.id : item.id;
    item.messages = Array.isArray(saved.messages) ? saved.messages.filter(function (message) {
      return message && ["user", "ai"].indexOf(message.role) >= 0 && typeof message.content === "string";
    }) : empty().messages;
    item.draft = typeof item.draft === "string" ? item.draft : "";
    item.task = item.task && typeof item.task.requestId === "string" && typeof item.task.goal === "string" ? item.task : null;
    var first = item.messages.find(function (message) { return message.role === "user"; });
    item.title = typeof saved.title === "string" ? titleFor(saved.title) : titleFor(first ? first.content : "新会话");
    item.createdAt = typeof saved.createdAt === "number" ? saved.createdAt : item.createdAt;
  }
  return item;
}

// The app owns all conversation pollers. Route or tab changes do not cancel tasks.
export function restoreGeneration() {
  epoch += 1;
  Object.keys(timers).forEach(function (id) { window.clearTimeout(timers[id]); });
  timers = {}; inFlight = {};
  userId = session.token ? session.userId : null;
  var saved = null;
  if (userId) { try { saved = JSON.parse(window.localStorage.getItem(key()) || "null"); } catch (error) { /* Invalid cache starts fresh. */ } }
  var items = [];
  if (userId) {
    if (saved && saved.version === 2 && Array.isArray(saved.conversations)) {
      saved.conversations.forEach(function (raw) {
        if (!raw || typeof raw !== "object") return;
        var item = conversation(raw);
        if (items.some(function (existing) { return existing.id === item.id; })) item.id = uuid();
        items.push(item);
      });
    } else if (saved && typeof saved === "object") {
      items.push(conversation(saved)); // Migrate the original single-conversation cache.
    }
    if (!items.length) items.push(conversation());
  }
  generation.conversations = items;
  generation.activeConversationId = saved && items.some(function (item) { return item.id === saved.activeConversationId; }) ? saved.activeConversationId : (items[0] ? items[0].id : null);
  generation.persistenceError = "";
  restoreActivePlan(); publish();
  var version = epoch;
  items.forEach(function (item) { if (item.task) poll(item.id, version); });
}

export function createConversation() {
  if (!userId) return;
  var item = conversation();
  generation.conversations.push(item);
  generation.activeConversationId = item.id;
  publish(); return item.id;
}
export function selectConversation(id) {
  if (!find(id)) return;
  generation.activeConversationId = id;
  publish();
}
export function deleteConversation(id) {
  var index = generation.conversations.findIndex(function (item) { return item.id === id; });
  if (index < 0) return;
  window.clearTimeout(timers[id]); delete timers[id];
  generation.conversations.splice(index, 1);
  if (!generation.conversations.length && userId) generation.conversations.push(conversation());
  if (generation.activeConversationId === id) {
    var next = generation.conversations[Math.min(index, generation.conversations.length - 1)];
    generation.activeConversationId = next ? next.id : null;
  }
  publish();
}
export function saveDraft(value) {
  var current = active(); if (!current) return;
  current.draft = value; publish();
}
export function startGeneration() {
  var current = active();
  if (!current || !userId) return;
  var goal = current.draft.trim();
  if (!goal || current.task) return;
  var history = current.messages.slice(-20).map(function (message) { return { role: message.role === "user" ? "user" : "assistant", content: message.content.slice(0, 3000) }; });
  if (!current.messages.some(function (message) { return message.role === "user"; })) current.title = titleFor(goal);
  current.task = { requestId: uuid(), goal: goal, submitted: false, history: history };
  current.error = ""; current.stage = "conversation";
  current.currentStageMessage = "正在思考回复";
  current.messages.push({ role: "user", content: goal });
  current.draft = "";
  publish(); // Persist the id before submission: refresh retries the same task, not a new one.
  poll(current.id, epoch);
}

async function poll(id, version) {
  var current = find(id);
  var task = current && current.task;
  if (!task || version !== epoch || inFlight[id]) return;
  var marker = {}; inFlight[id] = marker;
  var delay = 3000;
  function live() { return version === epoch && find(id) === current && current.task === task; }
  try {
    if (!task.submitted) {
      await submitPlan(task.goal, task.requestId, task.history || []);
      if (!live()) return;
      task.submitted = true; publish();
    }
    var snapshot = await getPlanTask(task.requestId);
    if (!live()) return;
    current.error = ""; current.stage = snapshot.stage; current.currentStageMessage = snapshot.message;
    if (snapshot.status === "completed") {
      if (snapshot.result.type === "chat" || snapshot.result.status === "replied") {
        current.task = null; current.currentStageMessage = "";
        current.messages.push({ role: "ai", content: snapshot.result.reply });
        publish(); return;
      }
      current.plan = snapshot.result;
      setActivePlan(snapshot.result.plan); publish();
      try { await planApi.replaceMonthly(snapshot.result.plan); }
      catch (error) {
        if (!live()) return;
        current.error = "计划已生成并缓存，服务器保存失败，正在自动重试：" + error.message;
        delay = 5000; publish(); return;
      }
      if (!live()) return;
      current.task = null;
      current.currentStageMessage = "计划已生成，已更新到今日计划";
      current.messages.push({ role: "ai", content: (snapshot.result.reply || "计划已生成并保存，可在今日计划中查看。") + " 本次目标：" + snapshot.result.plan.goal });
    } else if (snapshot.status === "failed") {
      current.task = null; current.error = snapshot.error || "生成失败，请重试";
      current.messages.push({ role: "ai", content: current.error });
    }
    publish();
  } catch (error) {
    if (!live()) return;
    current.error = error.message;
    if ([400, 401, 404, 422].indexOf(error.status) >= 0) {
      current.draft = task.goal; current.task = null;
    } else {
      current.currentStageMessage = "连接暂时中断，正在恢复任务状态（不会重新生成）";
    }
    publish();
  } finally {
    if (inFlight[id] === marker) delete inFlight[id];
    if (live()) timers[id] = window.setTimeout(function () { poll(id, version); }, delay);
  }
}
