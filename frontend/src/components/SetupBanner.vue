<template>
  <div v-if="visible" class="ob-setup-banner">
    <span>
      ⚠️ <strong>Setup incomplete.</strong>
      Configure your timezone, at least one SMTP channel, and password recovery.
      <strong>Without password recovery, losing your password means losing access to your data.</strong>
    </span>
    <div style="display: flex; gap: 8px; flex-shrink: 0;">
      <RouterLink :to="{ name: 'settings' }" class="ob-btn-inline">Set up now →</RouterLink>
      <button class="ob-btn-dismiss" @click="dismiss">Remind me later</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";

const auth = useAuthStore();
const ui = useUiStore();

const setupComplete = computed(() => {
  const user = auth.user;
  if (!user) return true;
  return user.timezone !== "UTC" && user.recovery_email !== null && user.password_reset_enabled;
});

const visible = computed(() => !setupComplete.value && !ui.setupDismissed);

function dismiss(): void {
  ui.dismissSetup();
}
</script>

<style scoped lang="scss">
.ob-setup-banner {
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: var(--ob-radius);
  padding: 12px 16px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  font-size: 13px;
  flex-wrap: wrap;
}

.ob-btn-inline {
  color: var(--ob-primary);
  font-weight: 600;
  font-size: 13px;
  text-decoration: none;
  white-space: nowrap;

  &:hover { text-decoration: underline; }
}

.ob-btn-dismiss {
  background: none;
  border: 1px solid #adb5bd;
  border-radius: 4px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
  color: var(--ob-text-muted);
  white-space: nowrap;

  &:hover { background: #e9ecef; }
}
</style>
