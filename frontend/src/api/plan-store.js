import Vue from "vue";
import { session } from "./session";

function storageKey() { return "fitness-copilot-active-plan-" + (session.userId || "anonymous"); }
function read() { try { return JSON.parse(window.localStorage.getItem(storageKey()) || "null"); } catch (error) { return null; } }

export var activePlan = Vue.observable({ value: read() });
export function setActivePlan(plan) { activePlan.value = plan; window.localStorage.setItem(storageKey(), JSON.stringify(plan)); }
