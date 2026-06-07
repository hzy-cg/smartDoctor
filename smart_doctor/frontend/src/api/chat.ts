import api from "./index";
import type { ApiResponse, Conversation, Message, SendMessageResponse } from "@/types";

const API_BASE = import.meta.env.VITE_API_BASE || "/api/v1";

export async function createConversation(doctorId: string) {
  return api.post<ApiResponse<Conversation>>("/chat/conversations", {
    doctor_id: doctorId,
  });
}

export async function getConversations() {
  return api.get<ApiResponse<Conversation[]>>("/chat/conversations");
}

export async function getMessages(conversationId: string) {
  return api.get<ApiResponse<Message[]>>(
    `/chat/conversations/${conversationId}/messages`,
  );
}

export async function sendMessage(conversationId: string, content: string) {
  return api.post<ApiResponse<SendMessageResponse>>(
    `/chat/conversations/${conversationId}/messages`,
    { content, input_type: "text" },
  );
}

export async function sendMessageStream(
  conversationId: string,
  content: string,
  onChunk: (chunk: string) => void,
  onDone: (sources: Array<{ source: string; content: string }>) => void,
  onError: (error: string) => void,
): Promise<void> {
  const token = localStorage.getItem("token");
  try {
    const response = await fetch(`${API_BASE}/chat/conversations/${conversationId}/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify({ content, input_type: "text" }),
    });

    if (!response.ok) {
      onError(`HTTP ${response.status}: ${response.statusText}`);
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      onError("无法读取响应流");
      return;
    }

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === "chunk") {
              onChunk(data.content);
            } else if (data.type === "done") {
              onDone(data.sources || []);
            } else if (data.type === "error") {
              onError(data.content);
            }
          } catch {
            // skip invalid JSON
          }
        }
      }
    }

    // Handle remaining buffer
    if (buffer.startsWith("data: ")) {
      try {
        const data = JSON.parse(buffer.slice(6));
        if (data.type === "chunk") {
          onChunk(data.content);
        } else if (data.type === "done") {
          onDone(data.sources || []);
        } else if (data.type === "error") {
          onError(data.content);
        }
      } catch {
        // skip invalid JSON
      }
    }
  } catch (e) {
    onError(e instanceof Error ? e.message : "网络连接失败");
  }
}
