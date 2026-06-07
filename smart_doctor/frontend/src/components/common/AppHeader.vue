<template>
  <header class="hdr">
    <div class="hdr-inner">
      <div class="hdr-brand" @click="$router.push('/chat')">
        <div class="brand-ico">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
        </div>
        <span class="brand-txt">SmartDoctor</span>
      </div>
      <nav class="hdr-nav">
        <router-link to="/doctors" class="nav-i" :class="{on:$route.path==='/doctors'}">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          医生
        </router-link>
        <router-link to="/chat" class="nav-i" :class="{on:$route.path==='/chat'}">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          问诊
        </router-link>
        <router-link to="/history" class="nav-i" :class="{on:$route.path==='/history'}">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          历史
        </router-link>
        <router-link to="/knowledge" class="nav-i" :class="{on:$route.path==='/knowledge'}">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          知识库
        </router-link>
        <router-link to="/settings" class="nav-i" :class="{on:$route.path==='/settings'}">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
          设置
        </router-link>
      </nav>
      <button class="logout" @click="handleLogout">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        退出
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { useUserStore } from "@/stores/user";
const router = useRouter();
const userStore = useUserStore();
const handleLogout = () => { userStore.logout(); router.push("/login"); };
</script>

<style scoped>
.hdr { height: 56px; background: #fff; border-bottom: 1px solid var(--c-neutral-200); flex-shrink: 0; position: relative; z-index: 100; }
.hdr::after { content:''; position:absolute; bottom:0; left:0; right:0; height:2px; background:linear-gradient(90deg,var(--c-primary),var(--c-primary-200),var(--c-primary)); opacity:.5; }
.hdr-inner { max-width:1400px; margin:0 auto; height:100%; display:flex; align-items:center; justify-content:space-between; padding:0 24px; }
.hdr-brand { display:flex; align-items:center; gap:9px; cursor:pointer; transition:opacity .2s; }
.hdr-brand:hover { opacity:.75; }
.brand-ico { width:34px; height:34px; border-radius:9px; background:linear-gradient(135deg,var(--c-primary),var(--c-primary-dark)); display:flex; align-items:center; justify-content:center; color:#fff; box-shadow:0 2px 8px rgba(13,148,136,.25); }
.brand-txt { font-family:'DM Sans',sans-serif; font-size:17px; font-weight:700; color:var(--c-neutral-800); letter-spacing:-.02em; }
.hdr-nav { display:flex; align-items:center; gap:3px; }
.nav-i { display:flex; align-items:center; gap:5px; padding:7px 13px; border-radius:var(--radius-sm); color:var(--c-neutral-500); text-decoration:none; font-size:13px; font-weight:500; transition:var(--transition); }
.nav-i:hover { color:var(--c-primary-dark); background:var(--c-primary-50); }
.nav-i.on { color:var(--c-primary-dark); background:var(--c-primary-50); font-weight:600; }
.logout { display:flex; align-items:center; gap:5px; padding:7px 13px; border-radius:var(--radius-sm); border:1px solid var(--c-neutral-200); background:#fff; color:var(--c-neutral-500); font-size:12.5px; font-weight:500; cursor:pointer; transition:var(--transition); font-family:inherit; }
.logout:hover { color:var(--c-rose); border-color:var(--c-rose); background:var(--c-rose-50); }
</style>
