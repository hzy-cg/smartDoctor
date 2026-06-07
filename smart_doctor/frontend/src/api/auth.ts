import api from "./index";
import type { ApiResponse } from "@/types";

export async function login(username: string, password: string) {
  return api.post<ApiResponse<{ user_id: string; token: string }>>(
    "/auth/login",
    { username, password },
  );
}

export async function register(username: string, password: string) {
  return api.post<ApiResponse<{ user_id: string; token: string }>>(
    "/auth/register",
    { username, password },
  );
}
