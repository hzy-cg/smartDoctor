<template>
  <div class="sub-page">
    <div class="sp-hdr">
      <div class="sp-hdr-inner">
        <h1>对话历史</h1>
        <p>查看您过去的问诊记录，可点击继续未完成的问诊</p>
      </div>
    </div>
    <div class="sp-body">
      <div v-if="loading" class="sp-empty">
        <div class="sp-empty-ico">
          <n-spin size="medium" />
        </div>
        <h3>加载中...</h3>
        <p>正在获取您的问诊记录</p>
      </div>

      <div v-else-if="error" class="sp-empty">
        <div class="sp-empty-ico">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
        </div>
        <h3>加载失败</h3>
        <p>{{ error }}</p>
        <button class="sp-link" @click="fetchData">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
          重新加载
        </button>
      </div>

      <div v-else-if="!conversations.length" class="sp-empty">
        <div class="sp-empty-ico">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        </div>
        <h3>暂无历史记录</h3>
        <p>您还没有进行过问诊，快去开始吧</p>
        <router-link to="/doctors" class="sp-link">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
          开始问诊
        </router-link>
      </div>

      <div v-else class="list-wrap">
        <div class="list">
          <div v-for="c in conversations" :key="c.id" class="card" @click="openChat(c)">
            <div class="card-main">
              <div class="card-row">
                <div class="card-info">
                  <h3 class="card-title">{{ c.title || '问诊记录' }}</h3>
                  <div class="card-meta">
                    <span class="meta-item">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                      {{ getDoctorName(c.doctor_id) }}
                    </span>
                    <span class="meta-item">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                      {{ fmtDateTime(c.created_at) }}
                    </span>
                  </div>
                </div>
                <n-tag :type="stageType(c.diagnosis_stage)" size="small" :bordered="false" round>
                  {{ stageLabel(c.diagnosis_stage) }}
                </n-tag>
              </div>
              <div v-if="c.symptoms && c.symptoms.length" class="card-symptoms">
                <span class="symptom-label">症状：</span>
                <span v-for="(s, i) in c.symptoms.slice(0, 4)" :key="i" class="symptom-tag">{{ s }}</span>
                <span v-if="c.symptoms.length > 4" class="symptom-more">+{{ c.symptoms.length - 4 }}</span>
              </div>
              <div class="card-foot">
                <span class="foot-hint">点击继续问诊</span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { NSpin, NTag } from "naive-ui";
import { getConversations } from "@/api/chat";
import { useChatStore } from "@/stores/chat";
import { useDoctorStore } from "@/stores/doctor";
import type { Conversation } from "@/types";

const router = useRouter();
const chatStore = useChatStore();
const doctorStore = useDoctorStore();

const conversations = ref<Conversation[]>([]);
const loading = ref(true);
const error = ref("");

const STAGE_MAP: Record<string, { label: string; type: "default" | "info" | "warning" | "success" }> = {
  collecting: { label: "信息采集", type: "warning" },
  analyzing: { label: "智能分析", type: "info" },
  recommending: { label: "方案推荐", type: "success" },
  completed: { label: "已完成", type: "default" },
};

const stageLabel = (stage: string) => STAGE_MAP[stage]?.label || stage || "未知";
const stageType = (stage: string): "default" | "info" | "warning" | "success" => STAGE_MAP[stage]?.type || "default";

const getDoctorName = (doctorId: string) => {
  const doc = doctorStore.doctors.find((d) => d.id === doctorId);
  return doc?.name || "未知医生";
};

const fmtDateTime = (s: string) => {
  if (!s) return "";
  const d = new Date(s);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 86400000) {
    return "今天 " + d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  }
  if (diff < 172800000) {
    return "昨天 " + d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  }
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const time = d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  return `${year}-${month}-${day} ${time}`;
};

const fetchData = async () => {
  loading.value = true;
  error.value = "";
  try {
    const res = await getConversations();
    if (res.data.code === 0 && res.data.data) {
      conversations.value = res.data.data;
    } else {
      error.value = res.data.message || "获取历史记录失败";
    }
  } catch {
    error.value = "网络异常，请检查网络连接后重试";
  } finally {
    loading.value = false;
  }
};

const openChat = (c: Conversation) => {
  chatStore.currentConversationId = c.id;
  router.push("/chat");
};

onMounted(async () => {
  await doctorStore.fetchDoctors();
  await fetchData();
});
</script>

<style scoped>
.sub-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--c-neutral-50);
}
.sp-hdr {
  background: #fff;
  border-bottom: 1px solid var(--c-neutral-200);
  padding: 24px 32px;
  flex-shrink: 0;
}
.sp-hdr-inner {
  max-width: 1200px;
  margin: 0 auto;
}
.sp-hdr h1 {
  font-size: 22px;
  font-weight: 700;
  color: var(--c-neutral-800);
  margin-bottom: 3px;
}
.sp-hdr p {
  font-size: 13.5px;
  color: var(--c-neutral-400);
}

.sp-body {
  flex: 1;
  overflow-y: auto;
}

.sp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  animation: fadeUp 0.4s ease;
}
.sp-empty-ico {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-lg);
  background: var(--c-neutral-100);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--c-neutral-400);
  margin-bottom: 14px;
}
.sp-empty h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--c-neutral-600);
  margin-bottom: 3px;
}
.sp-empty p {
  font-size: 13px;
  color: var(--c-neutral-400);
  margin-bottom: 18px;
}
.sp-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  background: var(--c-primary-50);
  color: var(--c-primary-dark);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  transition: var(--transition);
  border: none;
  font-family: inherit;
  cursor: pointer;
}
.sp-link:hover {
  background: var(--c-primary-100);
}

.list-wrap {
  padding: 24px 32px;
}
.list {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.card {
  background: #fff;
  border: 1px solid var(--c-neutral-200);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: var(--transition);
  animation: fadeUp 0.35s ease both;
}
.card:hover {
  border-color: var(--c-primary-200);
  box-shadow: 0 6px 20px rgba(13, 148, 136, 0.08);
  transform: translateY(-2px);
}
.card:nth-child(1) { animation-delay: 0s; }
.card:nth-child(2) { animation-delay: 0.05s; }
.card:nth-child(3) { animation-delay: 0.1s; }
.card:nth-child(4) { animation-delay: 0.15s; }
.card:nth-child(5) { animation-delay: 0.2s; }
.card:nth-child(n+6) { animation-delay: 0.25s; }

.card-main {
  padding: 18px 22px;
}
.card-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.card-info {
  flex: 1;
  min-width: 0;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--c-neutral-800);
  margin-bottom: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.card-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12.5px;
  color: var(--c-neutral-500);
}
.meta-item svg {
  color: var(--c-neutral-400);
  flex-shrink: 0;
}

.card-symptoms {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 12px;
  flex-wrap: wrap;
}
.symptom-label {
  font-size: 12px;
  color: var(--c-neutral-400);
  flex-shrink: 0;
}
.symptom-tag {
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--c-neutral-100);
  color: var(--c-neutral-600);
  font-size: 11.5px;
}
.symptom-more {
  font-size: 11.5px;
  color: var(--c-neutral-400);
}

.card-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 5px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--c-neutral-100);
}
.foot-hint {
  font-size: 12px;
  color: var(--c-primary);
  font-weight: 500;
}
.card-foot svg {
  color: var(--c-primary);
}
</style>