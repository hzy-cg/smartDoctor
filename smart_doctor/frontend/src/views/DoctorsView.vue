<template>
  <div class="doc-page">
    <div class="pg-hdr">
      <div class="pg-hdr-inner">
        <h1 class="pg-title">选择问诊医生</h1>
        <p class="pg-sub">选择一位专科医生，开始 AI 智能问诊</p>
        <div class="filters">
          <div class="search-wrap">
            <svg class="s-ico" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input v-model="search" class="s-inp" placeholder="搜索医生姓名 / 科室"/>
            <button v-if="search" class="s-clr" @click="search=''"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
          </div>
          <div class="chips">
            <button class="chip" :class="{on:!filterSpecialty}" @click="filterSpecialty=null">全部</button>
            <button v-for="s in specialtyOptions" :key="s.value" class="chip" :class="{on:filterSpecialty===s.value}" @click="filterSpecialty=s.value">{{ s.label }}</button>
          </div>
        </div>
      </div>
    </div>
    <div class="pg-body">
      <div v-if="!filteredDoctors.length" class="empty">
        <div class="empty-ico"><svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg></div>
        <h3>暂无可选医生</h3><p>请联系管理员添加医生角色</p>
      </div>
      <div class="grid">
        <div v-for="d in filteredDoctors" :key="d.id" class="card" @click="startChat(d)">
          <div class="card-bar"></div>
          <div class="card-main">
            <div class="card-row">
              <div class="avatar">{{ d.name.charAt(0) }}</div>
              <div class="meta"><h3 class="name">{{ d.name }}</h3><div class="tags"><span class="tag tag-s">{{ d.specialty }}</span><span class="tag tag-t">{{ d.title }}</span></div></div>
            </div>
            <p class="expert">{{ d.expertise || '暂无擅长介绍' }}</p>
            <div class="card-foot">
              <div class="stars"><span v-for="i in 5" :key="i" :class="{lit:i<=Math.round(d.rating)}">★</span><span class="rv">{{ (d.rating ?? 0).toFixed(1) }}</span></div>
              <button class="go-btn">开始问诊 <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg></button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useDoctorStore } from "@/stores/doctor";
import { useChatStore } from "@/stores/chat";
import type { DoctorRole } from "@/types";

const router = useRouter();
const doctorStore = useDoctorStore();
const chatStore = useChatStore();
const search = ref("");
const filterSpecialty = ref<string|null>(null);

onMounted(() => doctorStore.fetchDoctors());
const specialtyOptions = computed(() => [...new Set(doctorStore.doctors.filter(d=>d.lifecycle_state==="active").map(d=>d.specialty))].map(s=>({label:s,value:s})));
const filteredDoctors = computed(() => {
  let l = doctorStore.doctors;
  if (filterSpecialty.value) l = l.filter(d=>d.specialty===filterSpecialty.value);
  if (search.value) { const k = search.value.toLowerCase(); l = l.filter(d=>d.name.toLowerCase().includes(k)||d.specialty.toLowerCase().includes(k)); }
  return l.filter(d=>d.lifecycle_state==="active");
});
const startChat = async (d: DoctorRole) => {
  try {
    await chatStore.startConversation(d.id);
    if (chatStore.currentConversationId) {
      router.push("/chat");
    }
  } catch {
    // 错误已在 store 中处理
  }
};
</script>

<style scoped>
.doc-page { height:100%; display:flex; flex-direction:column; background:var(--c-neutral-50); }
.pg-hdr { background:#fff; border-bottom:1px solid var(--c-neutral-200); padding:24px 32px; flex-shrink:0; }
.pg-hdr-inner { max-width:1200px; margin:0 auto; }
.pg-title { font-size:22px; font-weight:700; color:var(--c-neutral-800); margin-bottom:3px; }
.pg-sub { font-size:13.5px; color:var(--c-neutral-400); margin-bottom:18px; }
.filters { display:flex; align-items:center; gap:14px; flex-wrap:wrap; }
.search-wrap { display:flex; align-items:center; border:1.5px solid var(--c-neutral-200); border-radius:var(--radius-sm); padding:0 10px; background:var(--c-neutral-50); transition:var(--transition); min-width:220px; }
.search-wrap:focus-within { border-color:var(--c-primary-light); box-shadow:0 0 0 3px rgba(13,148,136,.08); background:#fff; }
.s-ico { color:var(--c-neutral-400); flex-shrink:0; }
.s-inp { flex:1; border:none; outline:none; background:transparent; padding:8px 6px; font-family:inherit; font-size:13px; color:var(--c-neutral-800); }
.s-inp::placeholder { color:var(--c-neutral-400); }
.s-clr { border:none; background:none; color:var(--c-neutral-400); cursor:pointer; padding:2px; display:flex; }
.chips { display:flex; gap:5px; flex-wrap:wrap; }
.chip { padding:5px 13px; border-radius:18px; border:1px solid var(--c-neutral-200); background:#fff; color:var(--c-neutral-500); font-size:12.5px; font-weight:500; cursor:pointer; transition:var(--transition); font-family:inherit; }
.chip:hover { border-color:var(--c-primary); color:var(--c-primary-dark); }
.chip.on { background:var(--c-primary); color:#fff; border-color:var(--c-primary); }

.pg-body { flex:1; overflow-y:auto; padding:24px 32px; }
.empty { display:flex; flex-direction:column; align-items:center; padding:72px 0; animation:fadeUp .4s ease; }
.empty-ico { width:64px; height:64px; border-radius:var(--radius-lg); background:var(--c-neutral-100); display:flex; align-items:center; justify-content:center; color:var(--c-neutral-400); margin-bottom:14px; }
.empty h3 { font-size:15px; font-weight:600; color:var(--c-neutral-600); margin-bottom:3px; }
.empty p { font-size:13px; color:var(--c-neutral-400); }

.grid { max-width:1200px; margin:0 auto; display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:14px; }
.card { background:#fff; border-radius:var(--radius-lg); border:1px solid var(--c-neutral-200); overflow:hidden; cursor:pointer; transition:var(--transition); animation:fadeUp .35s ease both; }
.card:hover { border-color:var(--c-primary-200); box-shadow:0 6px 20px rgba(13,148,136,.08); transform:translateY(-2px); }
.card-bar { height:3px; background:linear-gradient(90deg,var(--c-primary),var(--c-primary-200)); }
.card-main { padding:18px; }
.card-row { display:flex; gap:12px; margin-bottom:12px; }
.avatar { width:44px; height:44px; border-radius:var(--radius-md); background:linear-gradient(135deg,var(--c-primary),var(--c-primary-dark)); display:flex; align-items:center; justify-content:center; font-size:17px; font-weight:700; color:#fff; flex-shrink:0; }
.meta { flex:1; min-width:0; }
.name { font-size:15px; font-weight:600; color:var(--c-neutral-800); margin-bottom:5px; }
.tags { display:flex; gap:5px; }
.tag { padding:2px 7px; border-radius:5px; font-size:11px; font-weight:500; }
.tag-s { background:var(--c-primary-50); color:var(--c-primary-dark); }
.tag-t { background:var(--c-neutral-100); color:var(--c-neutral-600); }
.expert { font-size:12.5px; color:var(--c-neutral-500); line-height:1.55; margin-bottom:14px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.card-foot { display:flex; align-items:center; justify-content:space-between; padding-top:12px; border-top:1px solid var(--c-neutral-100); }
.stars { display:flex; align-items:center; gap:1px; font-size:13px; color:var(--c-neutral-300); }
.stars .lit { color:var(--c-amber); }
.rv { font-size:11px; color:var(--c-neutral-400); margin-left:4px; }
.go-btn { display:flex; align-items:center; gap:5px; padding:6px 14px; border-radius:var(--radius-sm); border:none; background:linear-gradient(135deg,var(--c-primary),var(--c-primary-dark)); color:#fff; font-family:inherit; font-size:12.5px; font-weight:500; cursor:pointer; transition:var(--transition); box-shadow:0 2px 6px rgba(13,148,136,.2); }
.go-btn:hover { box-shadow:0 4px 12px rgba(13,148,136,.3); transform:translateY(-1px); }
</style>
