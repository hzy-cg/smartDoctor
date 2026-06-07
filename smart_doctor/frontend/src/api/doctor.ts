import api from "./index";
import type { ApiResponse, DoctorRole } from "@/types";

export async function getDoctors(specialty?: string) {
  return api.get<ApiResponse<DoctorRole[]>>("/doctors", {
    params: specialty ? { specialty } : {},
  });
}

export async function getAllDoctors() {
  return api.get<ApiResponse<DoctorRole[]>>("/doctors", {
    params: { lifecycle_state: "all" },
  });
}

export async function getDoctor(doctorId: string) {
  return api.get<ApiResponse<DoctorRole>>(`/doctors/${doctorId}`);
}

export async function createDoctor(data: {
  name: string;
  title: string;
  specialty: string;
  expertise?: string;
  experience?: string;
  education?: string;
  rating?: number;
}) {
  return api.post<ApiResponse<DoctorRole>>("/doctors/create", data);
}

export async function activateDoctor(doctorId: string) {
  return api.put<ApiResponse<DoctorRole>>(`/doctors/${doctorId}/activate`);
}

export async function deactivateDoctor(doctorId: string) {
  return api.put<ApiResponse<null>>(`/doctors/${doctorId}/deactivate`);
}