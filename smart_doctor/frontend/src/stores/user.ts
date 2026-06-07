import { defineStore } from "pinia";
import { ref } from "vue";
import { login as apiLogin, register as apiRegister } from "@/api/auth";

export const useUserStore = defineStore("user", () => {
  const userId = ref(localStorage.getItem("userId") || "");
  const token = ref(localStorage.getItem("token") || "");
  const consented = ref(localStorage.getItem("consented") === "true");

  const setAuth = (id: string, tk: string) => {
    userId.value = id;
    token.value = tk;
    localStorage.setItem("userId", id);
    localStorage.setItem("token", tk);
  };

  const setConsented = () => {
    consented.value = true;
    localStorage.setItem("consented", "true");
  };

  const doLogin = async (username: string, password: string) => {
    const res = await apiLogin(username, password);
    if (res.data.code === 0 && res.data.data) {
      setAuth(res.data.data.user_id, res.data.data.token);
    }
    return res.data;
  };

  const doRegister = async (username: string, password: string) => {
    const res = await apiRegister(username, password);
    if (res.data.code === 0 && res.data.data) {
      setAuth(res.data.data.user_id, res.data.data.token);
    }
    return res.data;
  };

  const logout = () => {
    userId.value = "";
    token.value = "";
    consented.value = false;
    localStorage.clear();
  };

  return { userId, token, consented, doLogin, doRegister, logout, setConsented };
});
