<template>
  <div class="login-page">
    <div class="login-bg">
      <div class="bg-grid"></div>
      <div class="bg-orb bg-orb-1"></div>
      <div class="bg-orb bg-orb-2"></div>
    </div>
    <div class="login-center">
      <div class="login-brand">
        <div class="brand-mark">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
        </div>
        <h1 class="brand-name">SmartDoctor</h1>
        <p class="brand-sub">AI 智能问诊助手</p>
      </div>
      <div class="login-card">
        <div class="tabs">
          <button class="tab" :class="{on:tab==='login'}" @click="tab='login'">登录</button>
          <button class="tab" :class="{on:tab==='register'}" @click="tab='register'">注册</button>
          <div class="tab-line" :class="{right:tab==='register'}"></div>
        </div>
        <div class="form-wrap">
          <div v-if="tab==='login'" class="form-body" key="l">
            <label class="lbl">用户名</label>
            <div class="inp-wrap"><svg class="inp-ico" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg><input v-model="username" class="inp" placeholder="请输入用户名" @keyup.enter="handleLogin"/></div>
            <label class="lbl">密码</label>
            <div class="inp-wrap"><svg class="inp-ico" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg><input v-model="password" type="password" class="inp" placeholder="请输入密码" @keyup.enter="handleLogin"/></div>
            <button class="submit" :disabled="loading" @click="handleLogin"><span v-if="loading" class="spinner"></span><span v-else>登录</span></button>
          </div>
          <div v-else class="form-body" key="r">
            <label class="lbl">用户名</label>
            <div class="inp-wrap"><svg class="inp-ico" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg><input v-model="username" class="inp" placeholder="请输入用户名"/></div>
            <label class="lbl">密码</label>
            <div class="inp-wrap"><svg class="inp-ico" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg><input v-model="password" type="password" class="inp" placeholder="请输入密码"/></div>
            <button class="submit" :disabled="loading" @click="handleRegister"><span v-if="loading" class="spinner"></span><span v-else>注册</span></button>
          </div>
        </div>
      </div>
      <p class="login-foot">您的数据将被加密存储，仅用于优化问诊体验</p>
    </div>
    <n-modal v-model:show="showConsent" :mask-closable="false" preset="card" title="知情同意书" style="width:460px;border-radius:var(--radius-lg)">
      <div style="line-height:1.8;font-size:14px;color:var(--c-neutral-600)">
        <p>欢迎使用 SmartDoctor 智能问诊助手。</p>
        <p style="margin-top:10px"><strong>重要提示：</strong></p>
        <ul style="padding-left:18px;margin-top:6px"><li style="margin-bottom:4px">本系统提供的分析和建议<b>仅供参考</b>，不能替代专业医生诊断</li><li>如遇紧急症状，请立即拨打 <b>120</b></li><li>您的对话数据将被加密存储</li><li>您有权随时查看、导出或删除您的全部数据</li></ul>
      </div>
      <template #footer>
        <div style="display:flex;gap:10px;justify-content:flex-end">
          <button class="consent-no" @click="handleRefuse">拒绝</button>
          <button class="consent-yes" @click="handleConsent">同意并继续</button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { NModal, useMessage } from "naive-ui";
import { useUserStore } from "@/stores/user";

const router = useRouter();
const userStore = useUserStore();
const message = useMessage();
const username = ref("");
const password = ref("");
const loading = ref(false);
const showConsent = ref(false);
const tab = ref<"login"|"register">("login");

const handleLogin = async () => {
  if (!username.value || !password.value) { message.warning("请填写用户名和密码"); return; }
  loading.value = true;
  try { const r = await userStore.doLogin(username.value, password.value); r.code === 0 ? checkConsent() : message.error(r.message || "登录失败"); }
  catch { message.error("登录失败"); }
  finally { loading.value = false; }
};
const handleRegister = async () => {
  if (!username.value || !password.value) { message.warning("请填写用户名和密码"); return; }
  loading.value = true;
  try { const r = await userStore.doRegister(username.value, password.value); r.code === 0 ? checkConsent() : message.error(r.message || "注册失败"); }
  catch { message.error("注册失败"); }
  finally { loading.value = false; }
};
const checkConsent = () => { userStore.consented ? router.push("/doctors") : (showConsent.value = true); };
const handleConsent = () => { userStore.setConsented(); showConsent.value = false; router.push("/doctors"); };
const handleRefuse = () => { showConsent.value = false; userStore.logout(); message.warning("需要同意知情同意书才能使用问诊服务"); };
</script>

<style scoped>
.login-page { position: relative; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
.login-bg { position: absolute; inset: 0; background: linear-gradient(155deg, #f0fdfa 0%, #f8fafc 45%, #ecfdf5 100%); }
.bg-grid { position: absolute; inset: 0; background-image: radial-gradient(circle at 1px 1px, rgba(13,148,136,.05) 1px, transparent 0); background-size: 28px 28px; }
.bg-orb { position: absolute; border-radius: 50%; filter: blur(80px); }
.bg-orb-1 { width: 380px; height: 380px; background: rgba(13,148,136,.1); top: -80px; right: -80px; }
.bg-orb-2 { width: 280px; height: 280px; background: rgba(20,184,166,.07); bottom: -60px; left: -40px; }

.login-center { position: relative; z-index: 1; display: flex; flex-direction: column; align-items: center; width: 100%; max-width: 400px; padding: 0 20px; animation: fadeUp .5s ease; }
.login-brand { text-align: center; margin-bottom: 28px; }
.brand-mark { width: 52px; height: 52px; border-radius: 14px; background: linear-gradient(135deg, var(--c-primary), var(--c-primary-dark)); display: flex; align-items: center; justify-content: center; color: #fff; margin: 0 auto 14px; box-shadow: 0 4px 14px rgba(13,148,136,.3); }
.brand-name { font-family: 'DM Sans', sans-serif; font-size: 26px; font-weight: 700; color: var(--c-neutral-800); letter-spacing: -.02em; }
.brand-sub { font-size: 13px; color: var(--c-neutral-400); margin-top: 4px; }

.login-card { width: 100%; background: #fff; border-radius: var(--radius-xl); box-shadow: var(--shadow-lg); overflow: hidden; }
.tabs { display: flex; position: relative; border-bottom: 1px solid var(--c-neutral-100); padding: 0 8px; }
.tab { flex: 1; padding: 15px; border: none; background: none; font-family: inherit; font-size: 14px; font-weight: 500; color: var(--c-neutral-400); cursor: pointer; transition: color .2s; position: relative; z-index: 1; }
.tab.on { color: var(--c-primary-dark); font-weight: 600; }
.tab-line { position: absolute; bottom: 0; left: 8px; width: calc(50% - 8px); height: 2px; background: var(--c-primary); border-radius: 1px; transition: transform .25s ease; }
.tab-line.right { transform: translateX(100%); }

.form-wrap { padding: 24px 24px 20px; }
.form-body { animation: fadeIn .25s ease; }
.lbl { display: block; font-size: 12.5px; font-weight: 500; color: var(--c-neutral-500); margin-bottom: 5px; }
.inp-wrap { display: flex; align-items: center; border: 1.5px solid var(--c-neutral-200); border-radius: var(--radius-md); padding: 0 12px; margin-bottom: 16px; background: var(--c-neutral-50); transition: var(--transition); }
.inp-wrap:focus-within { border-color: var(--c-primary-light); box-shadow: 0 0 0 3px rgba(13,148,136,.08); background: #fff; }
.inp-ico { color: var(--c-neutral-400); flex-shrink: 0; }
.inp { flex: 1; border: none; outline: none; background: transparent; padding: 11px 8px; font-family: inherit; font-size: 14px; color: var(--c-neutral-800); }
.inp::placeholder { color: var(--c-neutral-400); }

.submit { width: 100%; padding: 12px; border: none; border-radius: var(--radius-md); background: linear-gradient(135deg, var(--c-primary), var(--c-primary-dark)); color: #fff; font-family: inherit; font-size: 15px; font-weight: 600; cursor: pointer; transition: var(--transition); box-shadow: 0 3px 10px rgba(13,148,136,.25); margin-top: 4px; }
.submit:hover:not(:disabled) { box-shadow: 0 5px 18px rgba(13,148,136,.35); transform: translateY(-1px); }
.submit:disabled { opacity: .65; cursor: not-allowed; }
.spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid rgba(255,255,255,.3); border-top-color: #fff; border-radius: 50%; animation: spin .5s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.login-foot { margin-top: 20px; text-align: center; font-size: 11.5px; color: var(--c-neutral-400); }

.consent-no { padding: 8px 18px; border-radius: var(--radius-sm); border: none; background: var(--c-neutral-100); color: var(--c-neutral-500); font-family: inherit; font-size: 13px; cursor: pointer; transition: var(--transition); }
.consent-no:hover { background: var(--c-neutral-200); }
.consent-yes { padding: 8px 18px; border-radius: var(--radius-sm); border: none; background: linear-gradient(135deg, var(--c-primary), var(--c-primary-dark)); color: #fff; font-family: inherit; font-size: 13px; font-weight: 500; cursor: pointer; box-shadow: 0 2px 8px rgba(13,148,136,.25); transition: var(--transition); }
.consent-yes:hover { box-shadow: 0 4px 12px rgba(13,148,136,.35); }
</style>
