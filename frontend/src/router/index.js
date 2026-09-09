import Vue from "vue";
import Router from "vue-router";
import DashboardView from "../views/DashboardView.vue";
import AssistantView from "../views/AssistantView.vue";
import ProfileView from "../views/ProfileView.vue";
import LoginView from "../views/LoginView.vue";
import { session } from "../api/session";

Vue.use(Router);

var router = new Router({
  mode: "hash",
  routes: [
    { path: "/login", component: LoginView, meta: { public: true, title: "登录" } },
    { path: "/", component: DashboardView, meta: { title: "今日计划" } },
    { path: "/assistant", component: AssistantView, meta: { title: "私人助理" } },
    { path: "/profile", component: ProfileView, meta: { title: "个人信息" } }
  ]
});

router.beforeEach(function (to, from, next) {
  if (!to.meta.public && !session.token) { next("/login"); return; }
  if (to.path === "/login" && session.token) { next("/"); return; }
  next();
});

export default router;
