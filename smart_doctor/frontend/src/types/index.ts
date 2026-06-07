export interface DoctorRole {
  id: string;
  name: string;
  title: string;
  specialty: string;
  expertise: string;
  experience: string;
  education: string;
  avatar_url: string;
  rating: number;
  lifecycle_state: string;
  has_digital_human: boolean;
  created_at: string;
  updated_at: string;
}

export interface Conversation {
  id: string;
  doctor_id: string;
  title: string;
  interaction_mode: string;
  diagnosis_stage: string;
  symptoms: string[];
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  input_type: "text" | "voice";
  sources?: Array<{ source: string; content: string }>;
  metadata?: {
    sources?: Array<{ doc: string; page: number }>;
    department?: { name: string; reason: string };
  };
  created_at: string;
}

export interface SendMessageResponse {
  user_message: Message;
  assistant_message: Message;
  sources?: Array<{ source: string; content: string; metadata?: Record<string, unknown> }>;
}

export interface ApiResponse<T> {
  code: number;
  data: T;
  message: string;
}

export interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ChatChunk {
  type: "chat_chunk";
  conversation_id: string;
  seq: number;
  chunk_type: "text" | "source" | "dept" | "disclaimer";
  content: unknown;
  is_final: boolean;
}

export interface KnowledgeDoc {
  id: string;
  doctor_id: string;
  filename: string;
  file_path: string;
  file_type: string;
  chunk_count: number;
  version: number;
  status: string;
  collection_name: string;
  uploaded_at: string;
}
