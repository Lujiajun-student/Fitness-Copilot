// Runs without a browser or an AI request: node tests/generation-state.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const babel = require('@babel/core');

const code = babel.transformSync(fs.readFileSync('src/api/generation-store.js', 'utf8'), {
  babelrc: false, configFile: false, plugins: ['@babel/plugin-transform-modules-commonjs']
}).code;
const flush = async () => { for (let i = 0; i < 15; i++) await Promise.resolve(); };

function client(storage, api) {
  const session = { token: 'login', userId: 1 };
  const timers = [];
  const saved = [];
  const exports = {};
  vm.runInNewContext(code, {
    exports, Uint8Array, console,
    window: { crypto: require('node:crypto').webcrypto,
      localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
      setTimeout: fn => { timers.push(fn); return timers.length; }, clearTimeout: () => {} },
    require: name => {
      if (name === 'vue') return { observable: value => value };
      if (name === './session') return { session };
      if (name === './agent') return api;
      if (name === './fitness') return { planApi: { replaceMonthly: async plan => { saved.push(plan); } } };
      if (name === './plan-store') return { setActivePlan: plan => { saved.push(plan); }, restoreActivePlan: () => {} };
      throw new Error(name);
    }
  });
  return { ...exports, session, timers, saved };
}

(async () => {
  const storage = new Map(); let submissions = 0; let id;
  const api = { submitPlan: async (goal, taskId) => { submissions++; id = taskId; },
    getPlanTask: async () => ({ status: 'running', stage: 'strength', message: '正在规划无氧训练' }) };
  const first = client(storage, api);
  first.restoreGeneration(); first.saveDraft('减脂'); first.startGeneration(); await flush();
  assert.equal(submissions, 1);
  assert.equal(first.generation.stage, 'strength');
  assert.ok(first.generation.task);
  // Menu changes use this same store; a new page instance uses persisted state.
  const refreshed = client(storage, api);
  refreshed.restoreGeneration(); await flush();
  assert.equal(submissions, 1, 'refresh must query the same task without another generation');
  assert.equal(refreshed.generation.task.requestId, id);
  assert.equal(refreshed.generation.messages[1].content, '减脂');
  api.getPlanTask = async () => ({ status: 'completed', result: { plan: { days: [], goal: '减脂' } } });
  refreshed.timers.pop()(); await flush();
  assert.equal(refreshed.generation.task, null);
  assert.equal(refreshed.saved.length, 2, 'result updates local plan and server plan');
  // A later chat reply keeps the existing monthly plan and sends prior dialogue.
  let dialogue;
  api.submitPlan = async (goal, taskId, messages) => { dialogue = messages; };
  api.getPlanTask = async () => ({ status: 'completed', stage: 'conversation', result: { type: 'chat', status: 'replied', reply: '训练后记得休息。' } });
  refreshed.saveDraft('训练后怎么恢复？'); refreshed.startGeneration(); await flush();
  assert.ok(dialogue.length > 1);
  assert.equal(refreshed.generation.messages.at(-1).content, '训练后记得休息。');
  assert.equal(refreshed.saved.length, 2, 'ordinary chat must not overwrite the plan');
  assert.ok(refreshed.generation.plan);
  // Changing account must not apply an in-flight result to the new account.
  let finish;
  const other = client(new Map(), { submitPlan: async () => {}, getPlanTask: () => new Promise(resolve => { finish = resolve; }) });
  other.restoreGeneration(); other.saveDraft('体能'); other.startGeneration(); await flush();
  other.session.userId = 2; other.restoreGeneration();
  finish({ status: 'completed', result: { plan: { days: [] } } }); await flush();
  assert.equal(other.generation.plan, null);
  assert.equal(other.saved.length, 0);
  // Existing users keep the original single-conversation chat and draft.
  const legacyStorage = new Map([['fitness-copilot-generation-1', JSON.stringify({
    draft: '继续聊聊', messages: [{ role: 'ai', content: '你好' }, { role: 'user', content: '旧的减脂咨询' }], task: null
  })]]);
  const legacy = client(legacyStorage, api);
  legacy.restoreGeneration();
  assert.equal(legacy.generation.conversations.length, 1);
  assert.equal(legacy.generation.conversations[0].title, '旧的减脂咨询');
  assert.equal(legacy.generation.draft, '继续聊聊');
  assert.equal(JSON.parse(legacyStorage.get('fitness-copilot-generation-1')).version, 2);

  // Tabs keep independent drafts, histories and pending tasks. Results target their owner.
  const finishes = new Map(); const requests = new Map(); const multiStorage = new Map();
  const multiApi = {
    submitPlan: async (goal, requestId, history) => { requests.set(goal, { requestId, history }); },
    getPlanTask: requestId => new Promise(resolve => { finishes.set(requestId, resolve); })
  };
  const multi = client(multiStorage, multiApi);
  multi.restoreGeneration(); const a = multi.generation.activeConversationId;
  multi.saveDraft('会话 A 的草稿'); const b = multi.createConversation();
  assert.equal(multi.generation.messages.length, 1);
  assert.equal(multi.generation.draft, '');
  multi.saveDraft('会话 B 的草稿'); multi.selectConversation(a);
  assert.equal(multi.generation.draft, '会话 A 的草稿');
  multi.saveDraft('A 的恢复咨询'); multi.startGeneration(); await flush();
  multi.selectConversation(b); assert.equal(multi.generation.draft, '会话 B 的草稿');
  multi.saveDraft('B 的饮食咨询'); multi.startGeneration(); await flush();
  assert.equal(requests.size, 2);
  assert.ok(!JSON.stringify(requests.get('B 的饮食咨询').history).includes('A 的恢复咨询'));
  finishes.get(requests.get('A 的恢复咨询').requestId)({ status: 'completed', result: { type: 'chat', reply: '只给 A 的回复' } }); await flush();
  assert.equal(multi.generation.activeConversationId, b);
  assert.ok(!multi.generation.messages.some(message => message.content === '只给 A 的回复'));
  assert.equal(multi.generation.conversations.find(item => item.id === a).messages.at(-1).content, '只给 A 的回复');
  assert.ok(multi.generation.task, 'B must still be running');
  finishes.get(requests.get('B 的饮食咨询').requestId)({ status: 'completed', result: { type: 'chat', reply: '只给 B 的回复' } }); await flush();
  assert.equal(multi.generation.messages.at(-1).content, '只给 B 的回复');
  multi.selectConversation(a);
  assert.equal(multi.generation.messages.at(-1).content, '只给 A 的回复');
  const multiReloaded = client(multiStorage, multiApi); multiReloaded.restoreGeneration();
  assert.equal(multiReloaded.generation.conversations.length, 2);
  assert.equal(multiReloaded.generation.activeConversationId, a);
  assert.equal(multiReloaded.generation.messages.at(-1).content, '只给 A 的回复');
  multiReloaded.deleteConversation(b);
  assert.equal(multiReloaded.generation.activeConversationId, a, 'deleting another tab does not switch the active one');
  multiReloaded.deleteConversation(a);
  assert.equal(multiReloaded.generation.conversations.length, 1, 'deleting the last tab creates a blank conversation');
  assert.notEqual(multiReloaded.generation.activeConversationId, a);
  assert.equal(multiReloaded.generation.messages.length, 1);
  assert.equal(multiReloaded.saved.length, 0, 'deleting conversations does not delete or replace the monthly plan');

  // A deleted pending conversation cannot receive a late reply or overwrite the plan.
  let deletedFinish;
  const deleted = client(new Map(), { submitPlan: async () => {}, getPlanTask: () => new Promise(resolve => { deletedFinish = resolve; }) });
  deleted.restoreGeneration(); const deletedId = deleted.generation.activeConversationId;
  deleted.saveDraft('生成会被删除的计划'); deleted.startGeneration(); await flush();
  deleted.deleteConversation(deletedId);
  deletedFinish({ status: 'completed', result: { plan: { days: [], goal: '旧结果' } } }); await flush();
  assert.equal(deleted.generation.messages.length, 1);
  assert.equal(deleted.generation.plan, null);
  assert.equal(deleted.saved.length, 0);

  // A completed plan in an inactive tab still saves without contaminating the visible chat.
  let backgroundFinish;
  const background = client(new Map(), { submitPlan: async () => {}, getPlanTask: () => new Promise(resolve => { backgroundFinish = resolve; }) });
  background.restoreGeneration(); const owner = background.generation.activeConversationId;
  background.saveDraft('后台生成计划'); background.startGeneration(); await flush();
  const visible = background.createConversation();
  backgroundFinish({ status: 'completed', result: { plan: { days: [], goal: '后台计划' } } }); await flush();
  assert.equal(background.saved.length, 2);
  assert.equal(background.generation.activeConversationId, visible);
  assert.equal(background.generation.plan, null);
  assert.equal(background.generation.messages.length, 1);
  background.selectConversation(owner);
  assert.ok(background.generation.plan);
  assert.ok(background.generation.messages.at(-1).content.includes('后台计划'));

  // Refresh resumes every pending conversation using its original request ID.
  const pendingStorage = new Map(); let submitted = 0; const polled = [];
  const pendingApi = { submitPlan: async () => { submitted++; }, getPlanTask: async id => { polled.push(id); return { status: 'running', stage: 'conversation', message: '处理中' }; } };
  const pending = client(pendingStorage, pendingApi); pending.restoreGeneration();
  pending.saveDraft('任务一'); pending.startGeneration(); await flush();
  pending.createConversation(); pending.saveDraft('任务二'); pending.startGeneration(); await flush();
  const ids = pending.generation.conversations.map(item => item.task.requestId);
  const restored = client(pendingStorage, pendingApi); restored.restoreGeneration(); await flush();
  assert.equal(submitted, 2, 'refresh does not resubmit either task');
  assert.deepEqual(polled.slice(-2).sort(), Array.from(ids).sort());
  restored.session.userId = 9; restored.restoreGeneration();
  assert.equal(restored.generation.conversations.length, 1);
  assert.equal(restored.generation.messages.length, 1, 'other accounts cannot see saved conversations');

  console.log('PASS: legacy migration, new/switch/delete tabs, drafts/history isolation, late replies, background plans, refresh recovery and account isolation');
})().catch(error => { console.error(error); process.exitCode = 1; });
