import Vue from "vue";
var saved = JSON.parse(window.localStorage.getItem("fitness-copilot-session") || "null");
export var session = Vue.observable({ token: saved ? saved.token : "", userId: saved ? saved.userId : null, account: saved ? saved.account : "", bio: "", avatarDataUrl: "" });
export function setSession(data) { session.token = data.token; session.userId = data.userId; session.account = data.account; window.localStorage.setItem("fitness-copilot-session", JSON.stringify({ token: data.token, userId: data.userId, account: data.account })); }
export function clearSession() { session.token = ""; session.userId = null; session.account = ""; session.bio = ""; session.avatarDataUrl = ""; window.localStorage.removeItem("fitness-copilot-session"); }
