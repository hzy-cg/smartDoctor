<template>
  <div class="admin-page">
    <div class="pg-hdr">
      <div class="pg-hdr-inner">
        <div class="pg-hdr-left">
          <h1 class="pg-title">医生角色管理</h1>
          <p class="pg-sub">管理医生角色的创建、激活与停用</p>
        </div>
        <n-button type="primary" @click="openCreateModal">
          <template #icon>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </template>
          创建医生
        </n-button>
      </div>
    </div>
    <div class="pg-body">
      <n-spin :show="loading">
        <n-card class="table-card" :bordered="false">
          <n-data-table
            :columns="columns"
            :data="doctors"
            :pagination="pagination"
            :row-key="(row: DoctorRole) => row.id"
            :bordered="false"
            :single-line="false"
            size="medium"
          />
        </n-card>
      </n-spin>
      <div v-if="!loading && !doctors.length" class="empty">
        <div class="empty-ico">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>
        </div>
        <h3>暂无医生角色</h3>
        <p>点击上方按钮创建第一个医生角色</p>
      </div>
    </div>

    <n-modal v-model:show="showCreateModal" preset="card" title="创建医生角色" style="width:520px;border-radius:var(--radius-lg)">
      <n-form ref="formRef" :model="formData" :rules="formRules" label-placement="left" label-width="80" require-mark-placement="right-hanging">
        <n-form-item label="医生姓名" path="name">
          <n-input v-model:value="formData.name" placeholder="请输入医生姓名" />
        </n-form-item>
        <n-form-item label="职称" path="title">
          <n-input v-model:value="formData.title" placeholder="如：主任医师、副主任医师" />
        </n-form-item>
        <n-form-item label="科室" path="specialty">
          <n-input v-model:value="formData.specialty" placeholder="如：心内科、神经内科" />
        </n-form-item>
        <n-form-item label="擅长领域" path="expertise">
          <n-input v-model:value="formData.expertise" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" placeholder="请输入擅长领域" />
        </n-form-item>
        <n-form-item label="从业经验" path="experience">
          <n-input v-model:value="formData.experience" placeholder="如：20年临床经验" />
        </n-form-item>
        <n-form-item label="教育背景" path="education">
          <n-input v-model:value="formData.education" placeholder="如：北京大学医学博士" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="modal-footer">
          <n-button @click="showCreateModal = false">取消</n-button>
          <n-button type="primary" :loading="creating" @click="handleCreate">确认创建</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h, computed } from "vue";
import { NButton, NTag, NSwitch, NDataTable, NModal, NCard, NForm, NFormItem, NInput, NSpin, useMessage } from "naive-ui";
import type { DataTableColumns, FormInst, FormRules } from "naive-ui";
import { getAllDoctors, createDoctor, activateDoctor, deactivateDoctor } from "@/api/doctor";
import type { DoctorRole } from "@/types";

const message = useMessage();
const loading = ref(true);
const creating = ref(false);
const showCreateModal = ref(false);
const doctors = ref<DoctorRole[]>([]);
const formRef = ref<FormInst | null>(null);

const formData = ref({
  name: "",
  title: "",
  specialty: "",
  expertise: "",
  experience: "",
  education: "",
});

const formRules: FormRules = {
  name: [{ required: true, message: "请输入医生姓名", trigger: "blur" }],
  title: [{ required: true, message: "请输入职称", trigger: "blur" }],
  specialty: [{ required: true, message: "请输入科室", trigger: "blur" }],
};

const pagination = computed(() => ({
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
  showQuickJumper: true,
}));

const stateMap: Record<string, { label: string; type: "success" | "default" }> = {
  active: { label: "激活", type: "success" },
  inactive: { label: "停用", type: "default" },
  draft: { label: "草稿", type: "default" },
};

const columns: DataTableColumns<DoctorRole> = [
  {
    title: "医生名称",
    key: "name",
    width: 140,
    render(row) {
      return h("div", { class: "cell-name" }, [
        h("span", { class: "cell-avatar" }, row.name.charAt(0)),
        h("span", { class: "cell-name-text" }, row.name),
      ]);
    },
  },
  {
    title: "职称",
    key: "title",
    width: 140,
  },
  {
    title: "科室",
    key: "specialty",
    width: 120,
    render(row) {
      return h(NTag, { type: "info", size: "small", bordered: false }, { default: () => row.specialty });
    },
  },
  {
    title: "状态",
    key: "lifecycle_state",
    width: 120,
    render(row) {
      const s = stateMap[row.lifecycle_state] || { label: row.lifecycle_state, type: "default" as const };
      return h(NTag, { type: s.type, size: "small", bordered: false }, { default: () => s.label });
    },
  },
  {
    title: "激活/停用",
    key: "toggle",
    width: 100,
    render(row) {
      return h(NSwitch, {
        modelValue: row.lifecycle_state === "active",
        onUpdateValue: (val: boolean) => handleToggle(row, val),
        size: "medium",
      });
    },
  },
  {
    title: "创建时间",
    key: "created_at",
    width: 180,
    render(row) {
      return row.created_at ? new Date(row.created_at).toLocaleString("zh-CN") : "-";
    },
  },
];

const fetchDoctors = async () => {
  loading.value = true;
  try {
    const res = await getAllDoctors();
    if (res.data.code === 0 && res.data.data) {
      doctors.value = res.data.data;
    } else {
      message.error(res.data.message || "获取医生列表失败");
    }
  } catch {
    message.error("获取医生列表失败");
  } finally {
    loading.value = false;
  }
};

const openCreateModal = () => {
  formData.value = { name: "", title: "", specialty: "", expertise: "", experience: "", education: "" };
  showCreateModal.value = true;
};

const handleCreate = async () => {
  try {
    await formRef.value?.validate();
  } catch {
    return;
  }
  creating.value = true;
  try {
    const res = await createDoctor({
      name: formData.value.name,
      title: formData.value.title,
      specialty: formData.value.specialty,
      expertise: formData.value.expertise || undefined,
      experience: formData.value.experience || undefined,
      education: formData.value.education || undefined,
      rating: 5.0,
    });
    if (res.data.code === 0) {
      message.success("医生创建成功");
      showCreateModal.value = false;
      await fetchDoctors();
    } else {
      message.error(res.data.message || "创建失败");
    }
  } catch {
    message.error("创建失败");
  } finally {
    creating.value = false;
  }
};

const handleToggle = async (row: DoctorRole, val: boolean) => {
  const oldState = row.lifecycle_state;
  const newState = val ? "active" : "inactive";
  row.lifecycle_state = newState;
  try {
    if (val) {
      const res = await activateDoctor(row.id);
      if (res.data.code === 0) {
        message.success(`已激活「${row.name}」`);
      } else {
        row.lifecycle_state = oldState;
        message.error(res.data.message || "激活失败");
      }
    } else {
      const res = await deactivateDoctor(row.id);
      if (res.data.code === 0) {
        message.success(`已停用「${row.name}」`);
      } else {
        row.lifecycle_state = oldState;
        message.error(res.data.message || "停用失败");
      }
    }
  } catch {
    row.lifecycle_state = oldState;
    message.error("操作失败");
  }
};

onMounted(fetchDoctors);
</script>

<style scoped>
.admin-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--c-neutral-50);
}
.pg-hdr {
  background: #fff;
  border-bottom: 1px solid var(--c-neutral-200);
  padding: 20px 32px;
  flex-shrink: 0;
}
.pg-hdr-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.pg-hdr-left {
  flex: 1;
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
.table-card {
  max-width: 1200px;
  margin: 0 auto;
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 72px 0;
  animation: fadeUp .4s ease;
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
.cell-name {
  display: flex;
  align-items: center;
  gap: 10px;
}
.cell-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--c-primary), var(--c-primary-dark));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}
.cell-name-text {
  font-weight: 500;
  color: var(--c-neutral-800);
}
.modal-footer {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}
</style>