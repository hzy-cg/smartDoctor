<template>
  <div class="chat-layout">
    <aside class="sidebar">
      <div class="sidebar-top">
        <button class="new-chat-btn" @click="newChat">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          新建问诊
        </button>
      </div>
      <div class="conv-list">
        <div
          v-for="c in chatStore.conversations" :key="c.id"
          class="conv-item" :class="{ active: c.id === chatStore.currentConversationId }"
          @click="switchConv(c.id)"
        >
          <div class="conv-dot"></div>
          <div class="conv-text">
            <div class="conv-title">{{ c.title || '问诊记录' }}</div>
            <div class="conv-time">{{ fmtDate(c.created_at) }}</div>
          </div>
        </div>
        <div v-if="!chatStore.conversations.length" class="conv-empty">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--c-neutral-300)"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          <span>暂无对话</span>
        </div>
      </div>
    </aside>

    <section class="chat-main">
      <div ref="msgBox" class="msg-scroll" @scroll.passive="onScroll">
        <div class="msg-scroll-inner">
          <div v-if="!chatStore.messages.length" class="welcome">
            <div class="welcome-icon">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
            </div>
            <h2 class="welcome-title">SmartDoctor AI 问诊</h2>
            <p class="welcome-sub">详细描述您的症状，AI 医生将为您智能分析</p>
            <div class="quick-tags">
              <button class="qtag" @click="fillInput('我最近经常头痛，伴有轻微头晕')">头痛头晕</button>
              <button class="qtag" @click="fillInput('咳嗽持续一周了，有少量痰')">持续咳嗽</button>
              <button class="qtag" @click="fillInput('胃部不适，饭后有胀气感')">胃部不适</button>
              <button class="qtag" @click="fillInput('晚上失眠，白天精神不好')">失眠乏力</button>
            </div>
          </div>

          <div v-for="msg in chatStore.messages" :key="msg.id" class="msg" :class="msg.role">
            <div v-if="msg.role==='assistant'" class="msg-avatar ai">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
            </div>
            <div class="msg-body" :class="msg.role">
              <div v-if="msg.role==='user'" class="msg-text">{{ msg.content }}</div>
              <div v-else class="msg-text md" v-html="renderMd(msg.content)"></div>
              <div v-if="msg.role==='assistant' && msg.sources && msg.sources.length" class="msg-sources">
                <div class="sources-label">📚 参考来源</div>
                <div v-for="(s, si) in msg.sources" :key="si" class="source-item">
                  <div class="source-doc">{{ s.source || '知识库文档' }}</div>
                  <div class="source-snippet">{{ s.content?.slice(0, 120) }}{{ (s.content?.length || 0) > 120 ? '...' : '' }}</div>
                </div>
              </div>
            </div>
            <div v-if="msg.role==='user'" class="msg-avatar me">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            </div>
          </div>

          <div v-if="chatStore.loading" class="msg assistant">
            <div class="msg-avatar ai"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg></div>
            <div class="msg-body assistant typing">
              <span class="dot"></span><span class="dot"></span><span class="dot"></span>
              <span class="typing-label">正在分析</span>
            </div>
          </div>

          <div v-if="chatStore.error" class="err-bar">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
            {{ chatStore.error }}
          </div>
        </div>
      </div>

      <transition name="fab-fade">
        <button
          v-show="showFab"
          class="scroll-bottom-fab"
          @click="scrollToBottom"
          aria-label="滚动到底部"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
          <span v-if="unreadCount > 0" class="fab-badge">{{ unreadCount }}</span>
        </button>
      </transition>

      <div class="input-dock">
        <div class="input-shell" :class="{ focus: focused, off: !chatStore.currentConversationId || chatStore.loading }">
          <textarea
            ref="taRef"
            v-model="text"
            class="input-area"
            :placeholder="ph"
            :disabled="!chatStore.currentConversationId || chatStore.loading"
            @focus="focused=true"
            @blur="focused=false"
            @keydown.enter.exact.prevent="send"
            @input="autoGrow"
          ></textarea>
          <div class="input-toolbar">
            <span class="char-hint" :class="{ warn: text.length>800 }">{{ text.length }}/1000</span>
            <button class="send-btn" :class="{ on: canSend }" :disabled="!canSend" @click="send">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>
        </div>
        <p class="dock-disclaimer">⚠️ AI 分析仅供参考，不能替代专业医生诊断，紧急情况请拨打 120</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from "vue";
import { useRouter } from "vue-router";
import { useChatStore } from "@/stores/chat";
import { useMessage } from "naive-ui";
import MarkdownIt from "markdown-it";

const router = useRouter();
const chatStore = useChatStore();
const msg = useMessage();
const text = ref("");
const focused = ref(false);
const msgBox = ref<HTMLElement | null>(null);
const taRef = ref<HTMLTextAreaElement | null>(null);
const md = new MarkdownIt({ html: false, breaks: true });
const renderMd = (t: string) => md.render(t);

const showFab = ref(false);
const unreadCount = ref(0);
const isNearBottom = ref(true);
let scrollRafId = 0;

const SCROLL_THRESHOLD = 160;

const ph = computed(() => {
  if (!chatStore.currentConversationId) return "请先选择医生开始问诊…";
  if (chatStore.loading) return "医生正在回复中…";
  return "请详细描述您的症状，如部位、持续时间、伴随症状等…";
});
const canSend = computed(() => text.value.trim() && chatStore.currentConversationId && !chatStore.loading);

const fmtDate = (s: string) => {
  if (!s) return "";
  const d = new Date(s), now = new Date(), diff = now.getTime() - d.getTime();
  if (diff < 86400000) return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  if (diff < 604800000) return ["周日","周一","周二","周三","周四","周五","周六"][d.getDay()];
  return d.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
};

const checkNearBottom = () => {
  const el = msgBox.value;
  if (!el) return true;
  return el.scrollHeight - el.scrollTop - el.clientHeight < SCROLL_THRESHOLD;
};

const onScroll = () => {
  if (scrollRafId) return;
  scrollRafId = requestAnimationFrame(() => {
    scrollRafId = 0;
    const near = checkNearBottom();
    isNearBottom.value = near;
    showFab.value = !near;
    if (near) unreadCount.value = 0;
  });
};

const scrollEnd = async (smooth = false) => {
  await nextTick();
  const el = msgBox.value;
  if (!el) return;
  requestAnimationFrame(() => {
    if (!el) return;
    if (smooth) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    } else {
      el.scrollTop = el.scrollHeight;
    }
    isNearBottom.value = true;
    showFab.value = false;
    unreadCount.value = 0;
  });
};

const scrollToBottom = () => {
  scrollEnd(true);
};

const autoGrow = () => {
  if (!taRef.value) return;
  taRef.value.style.height = "auto";
  taRef.value.style.height = Math.min(taRef.value.scrollHeight, 180) + "px";
};
const fillInput = (t: string) => { text.value = t; nextTick(autoGrow); };

watch(() => chatStore.messages.length, () => {
  if (isNearBottom.value) {
    scrollEnd();
  } else {
    unreadCount.value++;
  }
});

watch(() => chatStore.loading, (loading, wasLoading) => {
  if (!loading && wasLoading) {
    scrollEnd(true);
  }
});

onMounted(() => {
  chatStore.fetchConversations();
  if (chatStore.currentConversationId) {
    chatStore.fetchMessages(chatStore.currentConversationId).then(() => scrollEnd());
  }
});

onBeforeUnmount(() => {
  if (scrollRafId) cancelAnimationFrame(scrollRafId);
});

const switchConv = async (k: string) => {
  chatStore.currentConversationId = k;
  chatStore.streamingMessage = "";
  chatStore.streamingSources = [];
  unreadCount.value = 0;
  showFab.value = false;
  isNearBottom.value = true;
  await chatStore.fetchMessages(k);
  await scrollEnd();
};
const newChat = () => router.push("/doctors");
const send = async () => {
  const t = text.value.trim();
  if (!t || chatStore.loading) return;
  if (t.length > 1000) { msg.warning("请控制在1000字以内"); return; }
  text.value = "";
  if (taRef.value) taRef.value.style.height = "auto";
  isNearBottom.value = true;
  const err = await chatStore.sendMessageStream(t, () => {
    scrollEnd(true);
  });
  if (err) msg.error(err);
};
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: calc(100vh - 56px);
  overflow: hidden;
}

.sidebar {
  width: 272px;
  background: #fff;
  border-right: 1px solid var(--c-neutral-200);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.sidebar-top { padding: 16px; border-bottom: 1px solid var(--c-neutral-100); }
.new-chat-btn {
  width: 100%; display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 11px 0; border-radius: var(--radius-md); border: 1.5px dashed var(--c-primary);
  background: var(--c-primary-50); color: var(--c-primary-dark); font-size: 14px; font-weight: 600;
  cursor: pointer; transition: var(--transition); font-family: inherit;
}
.new-chat-btn:hover { background: var(--c-primary-100); }

.conv-list { flex: 1; overflow-y: auto; padding: 8px; }
.conv-item {
  display: flex; align-items: center; gap: 10px; padding: 11px 12px; border-radius: var(--radius-md);
  cursor: pointer; transition: var(--transition); margin-bottom: 2px;
}
.conv-item:hover { background: var(--c-neutral-50); }
.conv-item.active { background: var(--c-primary-50); outline: 1.5px solid var(--c-primary-200); }
.conv-dot {
  width: 8px; height: 8px; border-radius: 50%; background: var(--c-neutral-300); flex-shrink: 0;
}
.conv-item.active .conv-dot { background: var(--c-primary); }
.conv-text { flex: 1; min-width: 0; }
.conv-title { font-size: 13.5px; font-weight: 500; color: var(--c-neutral-700); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.conv-time { font-size: 11px; color: var(--c-neutral-400); margin-top: 2px; }
.conv-empty { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 48px 0; color: var(--c-neutral-400); font-size: 13px; }

.chat-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.msg-scroll {
  flex: 1 1 0%;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 28px 36px 0;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}
.msg-scroll-inner {
  padding-bottom: 28px;
}

.msg-scroll::-webkit-scrollbar {
  width: 6px;
}
.msg-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.msg-scroll::-webkit-scrollbar-thumb {
  background: var(--c-neutral-300);
  border-radius: 3px;
}
.msg-scroll::-webkit-scrollbar-thumb:hover {
  background: var(--c-primary-light);
}
.msg-scroll::-webkit-scrollbar-corner {
  background: transparent;
}

.scroll-bottom-fab {
  position: absolute;
  bottom: 110px;
  right: 44px;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: #fff;
  color: var(--c-primary);
  box-shadow: 0 2px 12px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.04);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.scroll-bottom-fab:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0,0,0,0.16), 0 0 0 1px rgba(0,0,0,0.04);
}
.scroll-bottom-fab:active {
  transform: translateY(0);
}
.fab-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: var(--c-rose);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  line-height: 18px;
  text-align: center;
  pointer-events: none;
}

.fab-fade-enter-active,
.fab-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.fab-fade-enter-from,
.fab-fade-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.85);
}

.welcome { display: flex; flex-direction: column; align-items: center; padding-top: 72px; animation: fadeUp .5s ease; }
.welcome-icon {
  width: 76px; height: 76px; border-radius: var(--radius-xl); margin-bottom: 20px;
  background: linear-gradient(135deg, var(--c-primary-50), var(--c-primary-100));
  display: flex; align-items: center; justify-content: center; color: var(--c-primary);
}
.welcome-title { font-family: 'DM Sans', sans-serif; font-size: 24px; font-weight: 700; color: var(--c-neutral-800); margin-bottom: 6px; }
.welcome-sub { font-size: 14px; color: var(--c-neutral-400); margin-bottom: 28px; }
.quick-tags { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; max-width: 480px; }
.qtag {
  padding: 8px 18px; border-radius: 20px; border: 1px solid var(--c-neutral-200); background: #fff;
  color: var(--c-neutral-600); font-size: 13px; cursor: pointer; transition: var(--transition); font-family: inherit;
}
.qtag:hover { border-color: var(--c-primary); color: var(--c-primary-dark); background: var(--c-primary-50); transform: translateY(-1px); }

.msg { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 20px; animation: fadeUp .25s ease both; }
.msg.user { justify-content: flex-end; }
.msg-avatar {
  width: 34px; height: 34px; border-radius: var(--radius-sm); display: flex; align-items: center;
  justify-content: center; flex-shrink: 0; margin-top: 2px;
}
.msg-avatar.ai { background: linear-gradient(135deg, var(--c-primary), var(--c-primary-dark)); }
.msg-avatar.me { background: linear-gradient(135deg, var(--c-neutral-600), var(--c-neutral-700)); }

.msg-body { max-width: 68%; border-radius: var(--radius-lg); padding: 12px 16px; line-height: 1.75; font-size: 14.5px; }
.msg-body.user { background: linear-gradient(135deg, var(--c-primary), var(--c-primary-dark)); color: #fff; border-bottom-right-radius: 4px; }
.msg-body.assistant { background: #fff; color: var(--c-neutral-800); border: 1px solid var(--c-neutral-200); border-bottom-left-radius: 4px; box-shadow: var(--shadow-sm); }

.msg-text { word-break: break-word; }
.msg-text.md :deep(p) { margin-bottom: 8px; }
.msg-text.md :deep(p:last-child) { margin-bottom: 0; }
.msg-text.md :deep(ul), .msg-text.md :deep(ol) { padding-left: 20px; margin-bottom: 8px; }
.msg-text.md :deep(strong) { color: var(--c-primary-dark); }
.msg-text.md :deep(code) { background: var(--c-neutral-100); padding: 1px 5px; border-radius: 4px; font-size: 13px; }
.msg-text.md :deep(blockquote) { border-left: 3px solid var(--c-primary-light); padding-left: 12px; margin: 8px 0; color: var(--c-neutral-500); }

.msg-sources {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--c-neutral-100);
}
.sources-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--c-primary);
  margin-bottom: 8px;
}
.source-item {
  background: var(--c-neutral-50);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  margin-bottom: 6px;
}
.source-item:last-child { margin-bottom: 0; }
.source-doc {
  font-size: 12px;
  font-weight: 600;
  color: var(--c-neutral-700);
  margin-bottom: 3px;
}
.source-snippet {
  font-size: 11.5px;
  color: var(--c-neutral-500);
  line-height: 1.5;
}

.msg-body.typing { display: flex; align-items: center; gap: 6px; padding: 14px 18px; }
.dot { width: 6px; height: 6px; border-radius: 50%; background: var(--c-primary); animation: pulse3 1.2s ease infinite; }
.dot:nth-child(2) { animation-delay: .15s; }
.dot:nth-child(3) { animation-delay: .3s; }
.typing-label { font-size: 13px; color: var(--c-neutral-400); margin-left: 4px; }

.err-bar { display: flex; align-items: center; gap: 6px; padding: 10px 16px; background: var(--c-rose-50); color: var(--c-rose); border-radius: var(--radius-md); font-size: 13px; margin: 8px 0; }

.input-dock {
  flex-shrink: 0;
  padding: 14px 36px 18px;
  background: var(--c-neutral-50);
  border-top: 1px solid var(--c-neutral-200);
}
.input-shell {
  max-width: 820px; margin: 0 auto; background: #fff; border: 2px solid var(--c-neutral-200);
  border-radius: var(--radius-xl); transition: var(--transition); overflow: hidden;
}
.input-shell.focus { border-color: var(--c-primary-light); box-shadow: 0 0 0 4px rgba(13,148,136,.08); }
.input-shell.off { opacity: .6; }

.input-area {
  display: block; width: 100%; padding: 16px 20px 6px; border: none; outline: none; resize: none;
  font-family: inherit; font-size: 15px; line-height: 1.65; color: var(--c-neutral-800);
  background: transparent; min-height: 56px; max-height: 180px;
}
.input-area::placeholder { color: var(--c-neutral-400); }
.input-area:disabled { cursor: not-allowed; }

.input-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 6px 14px 12px; }
.char-hint { font-size: 11px; color: var(--c-neutral-400); transition: color .2s; }
.char-hint.warn { color: var(--c-rose); }

.send-btn {
  width: 40px; height: 40px; border-radius: var(--radius-md); border: 1.5px solid var(--c-neutral-300);
  background: var(--c-neutral-300); color: var(--c-neutral-500); display: flex; align-items: center;
  justify-content: center; cursor: not-allowed; opacity: 0.5; transition: var(--transition);
}
.send-btn.on {
  background: linear-gradient(135deg, var(--c-primary), var(--c-primary-dark)); color: #fff;
  cursor: pointer; box-shadow: 0 3px 10px rgba(13,148,136,.3);
}
.send-btn.on:hover { transform: scale(1.06); box-shadow: 0 5px 16px rgba(13,148,136,.35); }

.dock-disclaimer { text-align: center; font-size: 11px; color: var(--c-neutral-400); margin-top: 8px; }

@media (max-width: 1024px) {
  .sidebar { width: 220px; }
  .msg-scroll { padding: 20px 24px 0; }
  .input-dock { padding: 12px 24px 16px; }
  .scroll-bottom-fab { right: 32px; bottom: 100px; }
}

@media (max-width: 768px) {
  .chat-layout { flex-direction: column; height: calc(100vh - 56px); }
  .sidebar {
    width: 100%;
    height: auto;
    max-height: 180px;
    border-right: none;
    border-bottom: 1px solid var(--c-neutral-200);
  }
  .conv-list { max-height: 120px; }
  .msg-scroll { padding: 16px 16px 0; }
  .msg-body { max-width: 82%; }
  .input-dock { padding: 10px 16px 14px; }
  .scroll-bottom-fab { right: 16px; bottom: 90px; width: 40px; height: 40px; }
}

@media (max-width: 480px) {
  .msg-scroll { padding: 12px 12px 0; }
  .msg-body { max-width: 88%; font-size: 14px; }
  .input-dock { padding: 8px 12px 12px; }
  .input-area { font-size: 16px; min-height: 48px; padding: 12px 16px 4px; }
  .scroll-bottom-fab { right: 12px; bottom: 80px; }
}
</style>
