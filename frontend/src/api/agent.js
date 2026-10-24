import { session } from "./session";

var agentBaseUrl = process.env.VUE_APP_AGENT_API_BASE_URL || "http://127.0.0.1:8001/api";

async function request(path, options) {
  var controller = new AbortController();
  var timeout = window.setTimeout(function () { controller.abort(); }, 10000);
  try {
    var response = await fetch(agentBaseUrl + path, Object.assign({}, options, {
      signal: controller.signal,
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + session.token }
    }));
    var data = await response.json().catch(function () { return {}; });
    if (!response.ok) { var error = new Error(data.detail || "AI 服务暂时不可用"); error.status = response.status; throw error; }
    return data;
  } finally { window.clearTimeout(timeout); }
}

export function submitPlan(goal, requestId, messages) {
  return request("/v1/assistant/messages", { method: "POST", body: JSON.stringify({ goal: goal, requestId: requestId, messages: messages || [] }) });
}
export function getPlanTask(taskId) { return request("/v1/plans/tasks/" + encodeURIComponent(taskId)); }
