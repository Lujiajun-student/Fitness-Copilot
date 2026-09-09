<template>
  <div v-if="isAuthenticated" id="fitness-app">
    <aside class="sidebar">
      <router-link class="brand" to="/">
        <span class="brand-mark">F</span>
        <span>FITNESS<br><strong>COPILOT</strong></span>
      </router-link>
      <nav class="nav-list" aria-label="主菜单">
        <router-link class="nav-item" exact to="/"><span>▦</span> 今日计划</router-link>
        <router-link class="nav-item" to="/assistant"><span>✦</span> 私人助理</router-link>
        <router-link class="nav-item" to="/profile"><span>◎</span> 个人信息</router-link>
      </nav>
      <div class="sidebar-goal">
        <span class="eyebrow">本月目标</span>
        <strong>持续减脂</strong>
        <small>第 8 / 30 天</small>
        <div class="progress"><span style="width: 27%"></span></div>
      </div>
    </aside>

    <section class="main-column">
      <header class="topbar">
        <div><span class="eyebrow">MONDAY · 09.01</span><h1>{{ pageTitle }}</h1></div>
        <div class="account-area">
          <button class="account-trigger" type="button" @click="isAccountMenuOpen = !isAccountMenuOpen" aria-label="打开账户菜单">
            <span class="avatar" :style="avatarStyle">{{ accountInitial }}</span><span>{{ session.account }}</span><span class="chevron">⌄</span>
          </button>
          <div v-if="isAccountMenuOpen" class="account-menu">
            <button type="button" @click="goToProfile">个人信息</button>
            <button class="logout" type="button" @click="logout">退出登录</button>
          </div>
        </div>
      </header>
      <main class="page-content"><router-view /></main>
    </section>
  </div>
  <router-view v-else />
</template>

<script>
import { clearSession, session } from "./api/session";
export default {
  data: function () {
    return { isAccountMenuOpen: false, session: session };
  },
  computed: {
    pageTitle: function () { return this.$route.meta.title || "今日计划"; },
    isAuthenticated: function () { return Boolean(this.session.token); },
    accountInitial: function () { return this.session.account ? this.session.account.slice(0, 1) : ""; },
    avatarStyle: function () { return this.session.avatarDataUrl ? { backgroundImage: "url(" + this.session.avatarDataUrl + ")" } : {}; }
  },
  methods: {
    goToProfile: function () { this.isAccountMenuOpen = false; this.$router.push("/profile"); },
    logout: function () { this.isAccountMenuOpen = false; clearSession(); this.$router.push("/login"); }
  }
};
</script>
