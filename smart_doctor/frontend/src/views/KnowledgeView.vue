<template>
  <div class="kb-page">
    <div class="pg-hdr">
      <div class="pg-hdr-inner">
        <div class="pg-hdr-top">
          <div>
            <h1 class="pg-title">知识库管理</h1>
            <p class="pg-sub">管理医学知识文档，提升问诊质量</p>
          </div>
          <n-select
            v-model:value="selectedDoctorId"
            :options="doctorOptions"
            placeholder="选择医生"
            :loading="doctorLoading"
            clearable
            style="width: 240px"
            @update:value="onDoctorChange"
          />
        </div>
      </div>
    </div>

    <div class="pg-body">
      <div v-if="!selectedDoctorId" class="empty">
        <div class="empty-ico kb-ico">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <line x1="19" y1="8" x2="19" y2="14" />
            <line x1="22" y1="11" x2="16" y2="11" />
          </svg>
        </div>
        <h3>请选择一位医生</h3>
        <p>请先在上方选择一位医生，然后即可上传知识文档</p>
      </div>

      <div v-else-if="!loading && !documents.length" class="empty">
        <div class="empty-ico kb-ico">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          </svg>
        </div>
        <h3>暂无知识文档</h3>
        <p>点击上传按钮添加医学知识文档</p>
        <n-button type="primary" @click="openUploadModal" style="margin-top:14px">
          <template #icon>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </template>
          上传文档
        </n-button>
      </div>

      <div v-else class="table-wrap">
        <div class="table-toolbar">
          <span class="doc-count">共 {{ documents.length }} 份文档</span>
          <n-button type="primary" @click="openUploadModal">
            <template #icon>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
              </svg>
            </template>
            上传文档
          </n-button>
        </div>
        <n-data-table
          :columns="columns"
          :data="documents"
          :loading="loading"
          :bordered="false"
          :single-line="false"
          size="medium"
        />
      </div>
    </div>

    <!-- 上传弹窗 -->
    <n-modal v-model:show="showUploadModal" preset="card" title="上传知识文档" style="width:580px" :mask-closable="!uploading">
      <div class="upload-form">
        <div class="form-item">
          <label class="form-label">选择文档 <span class="required">*</span></label>
          <div style="margin-bottom: 8px">
            <input
              type="file"
              ref="fileInput"
              accept=".txt,.md,.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx"
              style="display:none"
              @change="handleFileSelect"
            />
            <n-button size="small" @click="($refs.fileInput as HTMLInputElement).click()" :disabled="uploading">
              选择文件
            </n-button>
            <span style="margin-left:8px;font-size:12px;color:var(--c-neutral-400)">支持 TXT/MD/PDF/Word/PPT/Excel，最大 50MB</span>
          </div>

          <!-- 文件信息 -->
          <div v-if="fileInfo.name" class="file-info">
            <div class="file-info-row">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>
              <span>{{ fileInfo.name }}</span>
            </div>
            <div class="file-info-meta">
              {{ fileInfo.size }}
              <span v-if="fileInfo.encoding"> · {{ fileInfo.encoding }}</span>
            </div>
          </div>

          <!-- 上传进度条 -->
          <div v-if="uploading" class="upload-progress-wrap">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: uploadPercent + '%' }"></div>
            </div>
            <div class="progress-text">
              {{ uploadStatusText }}
              <span v-if="uploadProgress.uploadedChunks > 0">
                ({{ uploadProgress.uploadedChunks }}/{{ uploadProgress.totalChunks }} 片)
              </span>
            </div>
          </div>

          <!-- 小文本文件预览区 -->
          <textarea
            v-if="contentPreview"
            v-model="contentPreview"
            class="content-area"
            placeholder="请粘贴文档内容…"
            rows="4"
            readonly
          ></textarea>
          <div v-else-if="fileInfo.name && !contentPreview && !uploading" class="content-hint">
            文档已就绪，点击「确认上传」开始分片上传
          </div>
        </div>
      </div>
      <template #footer>
        <div class="modal-footer">
          <n-button @click="cancelUpload" :disabled="uploading && uploadPercent > 0 && uploadPercent < 100">
            {{ uploading ? "取消上传" : "取消" }}
          </n-button>
          <n-button
            type="primary"
            :loading="uploading"
            :disabled="!selectedFile || uploading"
            @click="handleUpload"
          >
            {{ uploading ? "上传中..." : "确认上传" }}
          </n-button>
        </div>
      </template>
    </n-modal>

    <n-modal v-model:show="showDeleteModal" preset="dialog" title="确认删除" type="warning" positive-text="确认删除" negative-text="取消" @positive-click="confirmDelete" @negative-click="cancelDelete">
      确定要删除文档「{{ deletingDoc?.filename }}」吗？删除后不可恢复。
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, h, onMounted, computed } from "vue";
import {
  NSelect,
  NDataTable,
  NButton,
  NModal,
  NTag,
  useMessage,
} from "naive-ui";
import { useDoctorStore } from "@/stores/doctor";
import api from "@/api";
import type { KnowledgeDoc, DoctorRole } from "@/types";
import { UploadManager, type UploadProgress } from "@/utils/UploadManager";

const doctorStore = useDoctorStore();
const message = useMessage();

const selectedDoctorId = ref<string | null>(null);
const documents = ref<KnowledgeDoc[]>([]);
const loading = ref(false);
const doctorLoading = ref(false);

const showUploadModal = ref(false);
const showDeleteModal = ref(false);
const uploading = ref(false);

// 文件信息
const fileInfo = ref<{ name: string; size: string; encoding: string }>({
  name: "", size: "", encoding: "",
});
const contentPreview = ref("");
let rawFileContent = "";
let selectedFile: File | null = null;
const PREVIEW_SIZE_LIMIT = 1024 * 100; // 100KB

// 上传进度
const uploadManager = new UploadManager();
const uploadPercent = ref(0);
const uploadProgress = ref<UploadProgress>({
  uploadId: "", filename: "", totalChunks: 0, uploadedChunks: 0,
  percent: 0, status: "init",
});
const uploadStatusText = computed(() => {
  const p = uploadProgress.value;
  if (p.status === "init") return "准备上传...";
  if (p.status === "uploading") return `正在上传 ${p.percent}%`;
  if (p.status === "completed") return "上传完成";
  if (p.status === "error") return p.error || "上传失败";
  if (p.status === "cancelled") return "已取消";
  return "";
});

const deletingDoc = ref<KnowledgeDoc | null>(null);

const doctorOptions = computed(() =>
  doctorStore.doctors
    .filter((d: DoctorRole) => d.lifecycle_state === "active")
    .map((d: DoctorRole) => ({
      label: `${d.name}（${d.specialty}）`,
      value: d.id,
    }))
);

onMounted(() => {
  doctorLoading.value = true;
  doctorStore.fetchDoctors().finally(() => {
    doctorLoading.value = false;
  });
});

const fetchKnowledge = async () => {
  if (!selectedDoctorId.value) return;
  loading.value = true;
  try {
    const res = await api.get("/knowledge", {
      params: { doctor_id: selectedDoctorId.value },
    });
    if (res.data.code === 0) {
      documents.value = res.data.data || [];
    } else {
      message.error(res.data.message || "获取知识库列表失败");
    }
  } catch {
    message.error("获取知识库列表失败");
  } finally {
    loading.value = false;
  }
};

const onDoctorChange = () => {
  documents.value = [];
  fetchKnowledge();
};

const openUploadModal = () => {
  fileInfo.value = { name: "", size: "", encoding: "" };
  contentPreview.value = "";
  rawFileContent = "";
  selectedFile = null;
  uploadPercent.value = 0;
  uploadProgress.value = {
    uploadId: "", filename: "", totalChunks: 0, uploadedChunks: 0,
    percent: 0, status: "init",
  };
  showUploadModal.value = true;
};

const formatSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
};

const tryRead = (file: File, encoding: string): Promise<string> => {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (ev) => resolve(ev.target?.result as string || "");
    reader.onerror = () => resolve("");
    reader.readAsText(file, encoding);
  });
};

const handleFileSelect = async (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;

  // 大小校验
  if (file.size > 50 * 1024 * 1024) {
    message.warning("文件大小不能超过 50MB");
    return;
  }

  selectedFile = file;

  // 文件元数据
  fileInfo.value = {
    name: file.name,
    size: formatSize(file.size),
    encoding: "",
  };

  // 小文本文件：尝试读取并显示预览
  if (file.size <= PREVIEW_SIZE_LIMIT) {
    // 限定文本类文件才预览
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (ext === "txt" || ext === "md") {
      let content = await tryRead(file, "UTF-8");
      let encoding = "UTF-8";
      if (content && /[\uFFFD]/g.test(content)) {
        const gbkContent = await tryRead(file, "GBK");
        if (gbkContent && !/[\uFFFD]/g.test(gbkContent)) {
          content = gbkContent;
          encoding = "GBK";
        }
      }
      rawFileContent = content;
      contentPreview.value = content;
      fileInfo.value.encoding = encoding;
    }
  }
};

const handleUpload = async () => {
  if (!selectedFile || !selectedDoctorId.value) {
    message.warning("请选择文件");
    return;
  }

  uploading.value = true;
  uploadPercent.value = 0;

  try {
    const result = await uploadManager.upload(
      selectedFile,
      selectedDoctorId.value,
      (progress) => {
        uploadProgress.value = progress;
        uploadPercent.value = progress.percent;
      }
    );

    if (result.status === "completed") {
      message.success("上传成功");
      showUploadModal.value = false;
      fetchKnowledge();
    }
  } catch (err: any) {
    if (err.message?.includes("cancelled") || err.name === "AbortError") {
      message.info("上传已取消");
    } else {
      message.error(err.message || "上传失败");
    }
  } finally {
    uploading.value = false;
  }
};

const cancelUpload = () => {
  if (uploading.value) {
    // 正在上传中，取消上传
    uploadManager.cancel(uploadProgress.value.uploadId);
    uploading.value = false;
  } else {
    showUploadModal.value = false;
  }
};

const handleDelete = (doc: KnowledgeDoc) => {
  deletingDoc.value = doc;
  showDeleteModal.value = true;
};

const confirmDelete = async () => {
  if (!deletingDoc.value) return;
  try {
    const res = await api.delete(`/knowledge/${deletingDoc.value.id}`);
    if (res.data.code === 0) {
      message.success("删除成功");
      fetchKnowledge();
    } else {
      message.error(res.data.message || "删除失败");
    }
  } catch {
    message.error("删除失败");
  } finally {
    deletingDoc.value = null;
  }
};

const cancelDelete = () => {
  deletingDoc.value = null;
};

const fmtTime = (s: string) => {
  if (!s) return "-";
  const d = new Date(s);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

const columns = [
  {
    title: "文件名",
    key: "filename",
    width: 260,
    ellipsis: { tooltip: true },
  },
  {
    title: "版本",
    key: "version",
    width: 80,
    align: "center" as const,
  },
  {
    title: "分块数",
    key: "chunk_count",
    width: 90,
    align: "center" as const,
  },
  {
    title: "状态",
    key: "status",
    width: 100,
    align: "center" as const,
    render(row: KnowledgeDoc) {
      const isActive = row.status === "active";
      return h(
        NTag,
        { type: isActive ? "success" : "default", size: "small", round: true },
        { default: () => (isActive ? "启用" : "停用") }
      );
    },
  },
  {
    title: "上传时间",
    key: "uploaded_at",
    width: 170,
    render(row: KnowledgeDoc) {
      return fmtTime(row.uploaded_at);
    },
  },
  {
    title: "操作",
    key: "actions",
    width: 90,
    align: "center" as const,
    render(row: KnowledgeDoc) {
      return h(
        NButton,
        {
          size: "small",
          type: "error",
          text: true,
          onClick: () => handleDelete(row),
        },
        { default: () => "删除" }
      );
    },
  },
];
</script>

<style scoped>
.kb-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--c-neutral-50);
}

.pg-hdr {
  background: #fff;
  border-bottom: 1px solid var(--c-neutral-200);
  padding: 24px 32px;
  flex-shrink: 0;
}
.pg-hdr-inner {
  max-width: 1200px;
  margin: 0 auto;
}
.pg-hdr-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}
.pg-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--c-neutral-800);
  margin-bottom: 3px;
}
.pg-sub {
  font-size: 13.5px;
  color: var(--c-neutral-400);
}

.pg-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 72px 0;
  animation: fadeUp 0.4s ease;
}
.empty-ico {
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
.kb-ico {
  background: var(--c-primary-50);
  color: var(--c-primary);
}
.empty h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--c-neutral-600);
  margin-bottom: 3px;
}
.empty p {
  font-size: 13px;
  color: var(--c-neutral-400);
}

.table-wrap {
  max-width: 1200px;
  margin: 0 auto;
  background: #fff;
  border-radius: var(--radius-lg);
  border: 1px solid var(--c-neutral-200);
  overflow: hidden;
  animation: fadeUp 0.35s ease both;
}
.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--c-neutral-200);
}
.doc-count {
  font-size: 13px;
  color: var(--c-neutral-500);
  font-weight: 500;
}

.upload-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--c-neutral-600);
}
.required {
  color: var(--c-rose);
}
.content-area {
  width: 100%;
  padding: 12px 14px;
  border: 1.5px solid var(--c-neutral-200);
  border-radius: var(--radius-md);
  font-family: inherit;
  font-size: 13.5px;
  line-height: 1.7;
  color: var(--c-neutral-800);
  background: var(--c-neutral-50);
  resize: vertical;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.content-area:focus {
  border-color: var(--c-primary-light);
  box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.08);
  background: #fff;
}
.content-area::placeholder {
  color: var(--c-neutral-400);
}

.file-info {
  padding: 12px 14px;
  border: 1.5px solid var(--c-primary-light);
  border-radius: var(--radius-md);
  background: rgba(13, 148, 136, 0.04);
}
.file-info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--c-neutral-800);
}
.file-info-meta {
  margin-top: 4px;
  font-size: 12.5px;
  color: var(--c-neutral-500);
}
.content-hint {
  padding: 10px 14px;
  border: 1.5px dashed var(--c-neutral-200);
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--c-neutral-500);
  text-align: center;
}

.upload-progress-wrap {
  margin-top: 4px;
}
.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--c-neutral-100);
  border-radius: 4px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--c-primary), var(--c-primary-light));
  border-radius: 4px;
  transition: width 0.3s ease;
}
.progress-text {
  margin-top: 6px;
  font-size: 12px;
  color: var(--c-neutral-500);
}

.modal-footer {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .pg-hdr {
    padding: 18px 20px;
  }
  .pg-hdr-top {
    flex-direction: column;
    gap: 14px;
  }
  .pg-body {
    padding: 16px;
  }
  .table-toolbar {
    padding: 12px 14px;
    flex-direction: column;
    gap: 10px;
    align-items: flex-start;
  }
}
</style>