import { apiRequest } from "./http";
export var authApi = { login: function (data) { return apiRequest("/api/auth/login", { method: "POST", body: JSON.stringify(data) }); }, register: function (data) { return apiRequest("/api/auth/register", { method: "POST", body: JSON.stringify(data) }); } };
export var profileApi = { get: function () { return apiRequest("/api/users/me"); }, update: function (data) { return apiRequest("/api/users/me", { method: "PATCH", body: JSON.stringify(data) }); } };
export var bodyApi = { latest: function () { return apiRequest("/api/body-measurements/latest"); }, create: function (data) { return apiRequest("/api/body-measurements", { method: "POST", body: JSON.stringify(data) }); } };
export var planApi = {
  latestMonthly: function () { return apiRequest("/api/plans/monthly/latest"); },
  replaceMonthly: function (plan) { return apiRequest("/api/plans/monthly", { method: "POST", body: JSON.stringify({ goal: plan.goal, planDate: plan.startDate, content: plan }) }); }
};
