<template>
  <section class="profile-page">
    <div class="profile-intro"><span class="eyebrow">YOUR PROFILE</span><h2>让计划更懂你</h2><p>账户资料用于个性化体验；身体数据仅在你主动展示时可见。</p></div>
    <form @submit.prevent="save" class="settings-form">
      <section class="settings-section account-section"><div class="section-title"><span class="section-number">01</span><div><h3>账户资料</h3><p>管理公开展示信息与登录凭证。</p></div></div>
        <div class="avatar-editor"><label class="avatar large" :style="avatarStyle"><input type="file" accept="image/*" @change="previewAvatar"><span v-if="!avatarUrl">{{ account.username.slice(0, 1) }}</span></label><div><h4>个人头像</h4><p>点击头像上传图片</p></div></div>
        <div class="form-grid"><label>用户名<input v-model="account.username" maxlength="50"></label><label>新密码<input v-model="account.password" type="password" placeholder="留空则不修改"></label><label class="full-width">个人简介<textarea v-model="account.bio" maxlength="160" placeholder="介绍一下你的训练目标"></textarea></label></div>
      </section>
      <section class="settings-section body-section"><div class="section-title"><span class="section-number">02</span><div><h3>身体数据</h3><p>用于生成计划。默认隐藏，点击眼睛图标后才显示。</p></div><button class="eye-button" type="button" @click="showBody = !showBody" :aria-label="showBody ? '隐藏身体数据' : '显示身体数据'">{{ showBody ? '◉' : '◌' }}</button></div>
        <div class="form-grid body-grid"><label v-for="field in bodyFields" :key="field.key">{{ field.label }}<div class="unit-input"><input v-model="body[field.key]" :type="showBody ? 'number' : 'password'" :aria-label="field.label" :step="field.step"><span>{{ field.unit }}</span></div></label></div>
      </section>
      <section class="settings-section"><div class="section-title"><span class="section-number">03</span><div><h3>训练与健康档案</h3><p>用于评估训练负荷与恢复风险。标记 * 的项目为生成计划前必填；伤病信息可填写“无”。</p></div></div>
        <div class="form-grid">
          <label>训练经验 *<select v-model="safety.trainingExperience"><option value="">请选择</option><option value="BEGINNER">新手（规律训练少于 3 个月）</option><option value="INTERMEDIATE">有一定基础</option><option value="ADVANCED">长期规律训练</option></select></label>
          <label>每周可训练天数 *<input v-model.number="safety.weeklyTrainingDays" type="number" min="1" max="7"></label>
          <label>单次可训练时长 *<div class="unit-input"><input v-model.number="safety.sessionDurationMinutes" type="number" min="15" max="240"><span>分钟</span></div></label>
          <label>平均睡眠时长 *<div class="unit-input"><input v-model.number="safety.averageSleepHours" type="number" min="1" max="24" step="0.5"><span>小时</span></div></label>
          <label class="full-width">可训练时段 *<textarea v-model="safety.availableTrainingTimes" placeholder="例如：周一、三、五 19:00-20:00；周末上午"></textarea></label>
          <label class="full-width">伤病或医疗限制 *<textarea v-model="safety.injuryOrMedicalNotes" placeholder="例如：无；或右膝旧伤，避免跳跃和深蹲大重量"></textarea></label>
          <label class="full-width">可用器械<textarea v-model="safety.availableEquipment" placeholder="例如：无器械、瑜伽垫、弹力带、哑铃、健身房"></textarea></label>
          <label class="full-width">饮食限制或忌口<textarea v-model="safety.dietaryRestrictions" placeholder="例如：无；乳糖不耐受；不吃海鲜"></textarea></label>
        </div>
      </section>
      <div class="save-row"><span v-if="saved" class="saved">已保存</span><span v-if="error" class="form-error">{{ error }}</span><button class="save-button" :disabled="saving" type="submit">{{ saving ? "保存中…" : "保存个人信息" }}</button></div>
    </form>
  </section>
</template>

<script>
import { bodyApi, profileApi } from "../api/fitness";
import { session } from "../api/session";
export default {
  data: function () { return {
    showBody: false, saved: false, saving: false, error: "", avatarUrl: "",
    account: { username: "", password: "", bio: "" },
    safety: { trainingExperience: "", weeklyTrainingDays: "", sessionDurationMinutes: "", availableTrainingTimes: "", availableEquipment: "", injuryOrMedicalNotes: "", averageSleepHours: "", dietaryRestrictions: "" },
    body: { heightCm: "", weightKg: "", chestCm: "", waistCm: "", hipCm: "", bodyFatPercent: "" },
    bodyFields: [
      { key: "heightCm", label: "身高", unit: "cm", step: "0.1" }, { key: "weightKg", label: "体重", unit: "kg", step: "0.1" },
      { key: "chestCm", label: "胸围", unit: "cm", step: "0.1" }, { key: "waistCm", label: "腰围", unit: "cm", step: "0.1" },
      { key: "hipCm", label: "臀围", unit: "cm", step: "0.1" }, { key: "bodyFatPercent", label: "体脂率", unit: "%", step: "0.1" }
    ]
  }; },
  computed: { avatarStyle: function () { return this.avatarUrl ? { backgroundImage: "url(" + this.avatarUrl + ")" } : {}; } },
  created: function () { this.load(); },
  methods: {
    load: async function () {
      try { var profile = await profileApi.get(); this.account.username = profile.account; this.account.bio = profile.bio || ""; this.avatarUrl = profile.avatarDataUrl || ""; this.safety = { trainingExperience: profile.trainingExperience || "", weeklyTrainingDays: profile.weeklyTrainingDays || "", sessionDurationMinutes: profile.sessionDurationMinutes || "", availableTrainingTimes: profile.availableTrainingTimes || "", availableEquipment: profile.availableEquipment || "", injuryOrMedicalNotes: profile.injuryOrMedicalNotes || "", averageSleepHours: profile.averageSleepHours || "", dietaryRestrictions: profile.dietaryRestrictions || "" }; session.account = profile.account; session.bio = profile.bio || ""; session.avatarDataUrl = this.avatarUrl; var measurement = await bodyApi.latest(); if (measurement && measurement.id) { this.body = { heightCm: measurement.heightCm, weightKg: measurement.weightKg, chestCm: measurement.chestCm || "", waistCm: measurement.waistCm || "", hipCm: measurement.hipCm || "", bodyFatPercent: measurement.bodyFatPercent || "" }; } } catch (error) { this.error = error.message; }
    },
    previewAvatar: function (event) { var file = event.target.files[0]; if (file) { var reader = new FileReader(); var self = this; reader.onload = function () { self.avatarUrl = reader.result; }; reader.readAsDataURL(file); } },
    save: async function () { this.error = ""; this.saving = true; try { var profile = await profileApi.update(Object.assign({ account: this.account.username, bio: this.account.bio, avatarDataUrl: this.avatarUrl, newPassword: this.account.password || null }, this.safety)); session.account = profile.account; session.bio = profile.bio || ""; session.avatarDataUrl = profile.avatarDataUrl || ""; this.account.password = ""; await bodyApi.create(this.body); this.saved = true; var self = this; window.setTimeout(function () { self.saved = false; }, 2000); } catch (error) { this.error = error.message; } finally { this.saving = false; } }
  }
};
</script>
