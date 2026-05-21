import { defineStore } from "pinia";
import { ref } from "vue";

export const useUiStore = defineStore("ui", () => {
  const sidebarOpen = ref(true);
  const setupDismissed = ref(false);

  function toggleSidebar(): void {
    sidebarOpen.value = !sidebarOpen.value;
  }

  function dismissSetup(): void {
    setupDismissed.value = true;
  }

  return { sidebarOpen, setupDismissed, toggleSidebar, dismissSetup };
});
