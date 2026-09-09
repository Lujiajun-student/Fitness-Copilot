import Vue from "vue";
import App from "./App.vue";
import router from "./router";
import "./assets/styles.css";
import "./assets/dashboard.css";
import "./assets/profile.css";

Vue.config.productionTip = false;

new Vue({
  router,
  render: function (createElement) {
    return createElement(App);
  }
}).$mount("#app");
