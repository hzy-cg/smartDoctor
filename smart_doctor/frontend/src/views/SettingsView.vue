<template>
  <div class="sub-page">
    <div class="sp-hdr">
      <div class="sp-hdr-inner">
        <h1>设置</h1>
        <p>管理您的账户和偏好设置</p>
      </div>
    </div>
    <div class="sp-body">
      <n-space vertical :size="16" class="settings-list">
        <n-card title="个人信息" size="small" :bordered="true" class="s-card">
          <n-space vertical :size="12">
            <div class="info-row">
              <span class="info-label">用户 ID</span>
              <n-tag type="info" :bordered="false" size="small">{{ userStore.userId || '未知' }}</n-tag>
            </div>
            <n-divider style="margin: 4px 0" />
            <div class="info-row">
              <span class="info-label">知情同意</span>
              <n-tag :type="userStore.consented ? 'success' : 'warning'" :bordered="false" size="small">
                {{ userStore.consented ? '已同意' : '未同意' }}
              </n-tag>
            </div>
            <n-divider style="margin: 4px 0" />
            <n-button type="error" secondary @click="handleLogout" style="width: 100%">
              <template #icon>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
              </template>
              退出登录
            </n-button>
          </n-space>
        </n-card>

        <n-card title="问诊偏好" size="small" :bordered="true" class="s-card">
          <n-space vertical :size="12">
            <div class="pref-row">
              <div>
                <div class="pref-title">输入模式</div>
                <div class="pref-desc">选择默认的问诊输入方式</div>
              </div>
              <div class="pref-toggle">
                <span class="pref-label" :class="{ active: !voiceMode }">文本</span>
                <n-switch v-model:value="voiceMode" @update:value="onVoiceModeChange" />
                <span class="pref-label" :class="{ active: voiceMode }">语音</span>
              </div>
            </div>
          </n-space>
        </n-card>

        <n-card title="隐私设置" size="small" :bordered="true" class="s-card">
          <n-space vertical :size="8">
            <n-button text @click="showConsent = true" style="justify-content: flex-start; width: 100%">
              <template #icon>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
              </template>
              查看知情同意书
            </n-button>
            <n-divider style="margin: 4px 0" />
            <n-button text type="error" @click="handleClearHistory" style="justify-content: flex-start; width: 100%">
              <template #icon>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              </template>
              清除对话历史
            </n-button>
          </n-space>
        </n-card>

        <n-card title="关于" size="small" :bordered="true" class="s-card">
          <n-space vertical :size="8">
            <div class="about-row">
              <span class="info-label">版本号</span>
              <n-tag :bordered="false" size="small">v0.1.0</n-tag>
            </div>
            <n-divider style="margin: 4px 0" />
            <div class="about-row">
              <span class="info-label">技术架构</span>
              <span class="info-value">Vue 3 + TypeScript + Naive UI</span>
            </div>
            <n-divider style="margin: 4px 0" />
            <p class="about-disclaimer">
              SmartDoctor AI 智能问诊助手。本系统提供的分析和建议仅供参考，不能替代专业医生诊断。如遇紧急症状，请立即拨打 120。
            </p>
          </n-space>
        </n-card>
      </n-space>
    </div>

    <n-modal v-model:show="showConsent" preset="card" title="知情同意书" style="width: 500px">
      <div class="consent-content">
        <p>欢迎使用 SmartDoctor 智能问诊助手。</p>
        <p class="consent-strong">重要提示：</p>
        <ul>
          <li>本系统提供的分析和建议<b>仅供参考</b>，不能替代专业医生诊断</li>
          <li>如遇紧急症状，请立即拨打 <b>120</b></li>
          <li>您的对话数据将被加密存储</li>
          <li>您有权随时查看、导出或删除您的全部数据</li>
        </ul>
      </div>
    </n-modal>

    <n-modal v-model:show="showClearConfirm" preset="dialog" title="确认清除" type="warning" positive-text="确认清除" negative-text="取消" @positive-click="confirmClearHistory">
      <p>确定要清除所有对话历史记录吗？此操作不可恢复。</p>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue"
import { useRouter } from "vue-router"
import { NCard, NButton, NDivider, NSpace, NSwitch, NTag, NModal, useMessage } from "naive-ui"
import { useUserStore } from "@/stores/user"
import { useChatStore } from "@/stores/chat"

const router = useRouter()
const userStore = useUserStore()
const chatStore = useChatStore()
const message = useMessage()
const showConsent = ref(false)
const showClearConfirm = ref(false)
// TODO: 语音输入功能尚未实现
const voiceMode = ref(localStorage.getItem("voiceMode") === "true")

const onVoiceModeChange = (val: boolean) => {
  localStorage.setItem("voiceMode", String(val))
  message.success(val ? "已切换为语音输入模式" : "已切换为文本输入模式")
}

const handleLogout = () => {
  userStore.logout()
  message.success("已退出登录")
  router.push("/login")
}

const handleClearHistory = () => {
  showClearConfirm.value = true
}

const confirmClearHistory = () => {
  chatStore.conversations = []
  chatStore.messages = []
  message.success("本地聊天记录已清除")
}
</script>

<style scoped>
.sub-page { height: 100%; display: flex; flex-direction: column; background: var(--c-neutral-50) }
.sp-hdr { background: #fff; border-bottom: 1px solid var(--c-neutral-200); padding: 24px 32px; flex-shrink: 0 }
.sp-hdr-inner { max-width: 1200px; margin: 0 auto }
.sp-hdr h1 { font-size: 22px; font-weight: 700; color: var(--c-neutral-800); margin-bottom: 3px }
.sp-hdr p { font-size: 13.5px; color: var(--c-neutral-400) }
.sp-body { flex: 1; overflow-y: auto; padding: 24px 32px; display: flex; justify-content: center }
.settings-list { width: 100%; max-width: 600px; animation: fadeUp .35s ease }

.s-card {
  border-radius: var(--radius-lg) !important;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
}

.info-row { display: flex; align-items: center; justify-content: space-between }
.info-label { font-size: 14px; color: var(--c-neutral-600); font-weight: 500 }
.info-value { font-size: 13px; color: var(--c-neutral-500) }

.pref-row { display: flex; align-items: center; justify-content: space-between }
.pref-title { font-size: 14px; font-weight: 500; color: var(--c-neutral-600); margin-bottom: 2px }
.pref-desc { font-size: 12px; color: var(--c-neutral-400) }
.pref-toggle { display: flex; align-items: center; gap: 8px; flex-shrink: 0 }
.pref-label { font-size: 12.5px; color: var(--c-neutral-400); font-weight: 500; transition: color .2s }
.pref-label.active { color: var(--c-primary-dark); font-weight: 600 }

.about-row { display: flex; align-items: center; justify-content: space-between }
.about-disclaimer { font-size: 12.5px; color: var(--c-neutral-400); line-height: 1.7; margin: 0 }

.consent-content { line-height: 1.8; font-size: 14px; color: var(--c-neutral-600) }
.consent-content ul { padding-left: 18px; margin-top: 6px }
.consent-content li { margin-bottom: 4px }
.consent-strong { margin-top: 10px; font-weight: 600 }

@keyframes fadeUp { from { opacity: 0; transform: translateY(10px) } to { opacity: 1; transform: translateY(0) } }
</style>