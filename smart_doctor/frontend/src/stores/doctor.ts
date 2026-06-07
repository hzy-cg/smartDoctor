import { defineStore } from "pinia";
import { ref } from "vue";
import { getDoctors } from "@/api/doctor";
import type { DoctorRole } from "@/types";

export const useDoctorStore = defineStore("doctor", () => {
  const doctors = ref<DoctorRole[]>([]);
  const selectedDoctor = ref<DoctorRole | null>(null);

  const fetchDoctors = async (specialty?: string) => {
    try {
      const res = await getDoctors(specialty);
      if (res.data.code === 0 && res.data.data) {
        doctors.value = res.data.data;
      }
    } catch {
      // 错误已在 axios 拦截器中处理
    }
  };

  return { doctors, selectedDoctor, fetchDoctors };
});
