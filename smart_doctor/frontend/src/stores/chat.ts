import { defineStore } from "pinia";
import { ref } from "vue";
import {
  createConversation as apiCreateConv,
  getConversations as apiGetConvs,
  getMessages as apiGetMsgs,
  sendMessage as apiSendMsg,
  sendMessageStream as apiSendMsgStream,
} from "@/api/chat";
import type { Conversation, Message, SendMessageResponse } from "@/types";

export const useChatStore = defineStore("chat", () => {
  const conversations = ref<Conversation[]>([]);
  const messages = ref<Message[]>([]);
  const currentConversationId = ref("");
  const loading = ref(false);
  const error = ref("");
  const streamingMessage = ref("");
  const streamingSources = ref<Array<{ source: string; content: string }>>([]);

  const fetchConversations = async () => {
    try {
      const res = await apiGetConvs();
      if (res.data.code === 0 && res.data.data) {
        conversations.value = res.data.data;
      }
    } catch (e) {
      error.value = "获取对话列表失败";
      throw e;
    }
  };

  const startConversation = async (doctorId: string) => {
    try {
      const res = await apiCreateConv(doctorId);
      if (res.data.code === 0 && res.data.data) {
        currentConversationId.value = res.data.data.id;
        conversations.value.unshift(res.data.data);
        messages.value = [];
        streamingSources.value = [];
      }
    } catch {
      error.value = "创建对话失败";
    }
    return currentConversationId.value;
  };

  const fetchMessages = async (conversationId: string) => {
    try {
      const res = await apiGetMsgs(conversationId);
      if (res.data.code === 0 && res.data.data) {
        messages.value = res.data.data;
      }
    } catch (e) {
      error.value = "获取消息失败";
      throw e;
    }
  };

  const sendMessage = async (content: string): Promise<string | null> => {
    if (!currentConversationId.value) return "没有活跃的对话";
    loading.value = true;
    error.value = "";
    try {
      const res = await apiSendMsg(currentConversationId.value, content);
      if (res.data.code === 0 && res.data.data) {
        const data: SendMessageResponse = res.data.data;
        messages.value.push(data.user_message);
        messages.value.push(data.assistant_message);
        streamingSources.value = data.sources || [];
        return null;
      } else {
        error.value = res.data.message || "发送失败";
        return error.value;
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "网络错误";
      error.value = msg;
      return msg;
    } finally {
      loading.value = false;
    }
  };

  const sendMessageStream = async (content: string, onComplete: () => void): Promise<string | null> => {
    if (!currentConversationId.value) return "没有活跃的对话";
    loading.value = true;
    error.value = "";
    streamingMessage.value = "";
    streamingSources.value = [];

    const tempId = `temp-${crypto.randomUUID()}`;
    const assistantTempId = `temp-${crypto.randomUUID()}`;

    messages.value.push({
      id: tempId,
      conversation_id: currentConversationId.value,
      role: "user",
      content,
      input_type: "text",
      created_at: new Date().toISOString(),
    });

    messages.value.push({
      id: assistantTempId,
      conversation_id: currentConversationId.value,
      role: "assistant",
      content: "",
      input_type: "text",
      created_at: new Date().toISOString(),
    });

    try {
      await apiSendMsgStream(
        currentConversationId.value,
        content,
        (chunk: string) => {
          streamingMessage.value += chunk;
          const idx = messages.value.findIndex(m => m.id === assistantTempId);
          if (idx !== -1) {
            messages.value[idx] = { ...messages.value[idx], content: streamingMessage.value };
          }
        },
        (sources) => {
          streamingSources.value = sources;
          const idx = messages.value.findIndex(m => m.id === assistantTempId);
          if (idx !== -1) {
            messages.value[idx] = { ...messages.value[idx], sources };
          }
        },
        (err: string) => {
          error.value = err;
        },
      );
    } finally {
      loading.value = false;
      onComplete();
    }

    return error.value || null;
  };

  return {
    conversations, messages, currentConversationId,
    loading, error, streamingMessage, streamingSources,
    fetchConversations, startConversation,
    fetchMessages, sendMessage, sendMessageStream,
  };
});
