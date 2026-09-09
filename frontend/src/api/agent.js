import { session } from "./session";

// Agent uses a different service from the Java API. A direct local URL avoids
// accidental forwarding to the Java backend when the Vue dev proxy is stale.
var agentBaseUrl = process.env.VUE_APP_AGENT_API_BASE_URL || "http://127.0.0.1:8001/api";

export async function generatePlan(goal, onEvent) {
  var response = await fetch(agentBaseUrl + "/v1/plans/generate/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json", "Authorization": "Bearer " + session.token },
    body: JSON.stringify({ goal: goal })
  });
  if (!response.ok) {
    var payload = await response.json().catch(function () { return {}; });
    throw new Error(payload.detail || payload.message || "AI 服务暂时不可用，请稍后再试");
  }
  var reader = response.body.getReader();
  var decoder = new TextDecoder("utf-8");
  var buffer = "";
  var result = null;
  while (true) {
    var chunk = await reader.read();
    if (chunk.done) break;
    buffer += decoder.decode(chunk.value, { stream: true });
    var events = buffer.split("\n\n");
    buffer = events.pop();
    events.forEach(function (item) {
      var lines = item.split("\n");
      var type = (lines.find(function (line) { return line.indexOf("event:") === 0; }) || "event: message").slice(6).trim();
      var raw = (lines.find(function (line) { return line.indexOf("data:") === 0; }) || "data: {}").slice(5).trim();
      var data = JSON.parse(raw);
      if (type === "error") throw new Error(data.detail || "AI 服务暂时不可用");
      if (type === "result") result = data;
      if (type === "stage" && onEvent) onEvent(data);
    });
  }
  if (!result) throw new Error("AI 服务未返回计划结果");
  return result;
}
