import { defineStore } from "pinia";
import { ref } from "vue";
import type { User } from "@/api";
import { accountApi, authApi } from "@/api";

export const useAuthStore = defineStore("auth", () => {
  const user = ref<User | null>(null);
  const loading = ref(false);

  async function fetchMe(): Promise<void> {
    try {
      user.value = await accountApi.me();
    } catch {
      user.value = null;
    }
  }

  async function login(username: string, password: string): Promise<User> {
    loading.value = true;
    try {
      const u = await authApi.login(username, password);
      user.value = u;
      return u;
    } finally {
      loading.value = false;
    }
  }

  async function logout(): Promise<void> {
    await authApi.logout();
    user.value = null;
  }

  return { user, loading, fetchMe, login, logout };
});
