<template>
  <div>
    <h2 class="ob-page-title">Settings</h2>

    <div class="ob-card ob-form">
      <h3 class="ob-section-title">Timezone</h3>
      <div class="ob-field">
        <label>Your timezone (all schedule previews use this)</label>
        <select v-model="form.timezone">
          <option v-for="tz in timezones" :key="tz" :value="tz">{{ tz }}</option>
        </select>
      </div>

      <h3 class="ob-section-title" style="margin-top: 24px;">Password Recovery</h3>
      <label class="ob-checkbox" style="margin-bottom: 12px;">
        <input v-model="form.password_reset_enabled" type="checkbox" />
        Enable password reset via email
      </label>
      <div class="ob-field">
        <label>Recovery email address</label>
        <input v-model="form.recovery_email" type="email" placeholder="you@example.com" />
      </div>
      <div class="ob-field">
        <label>SMTP channel for recovery emails</label>
        <select v-model="form.recovery_channel_id">
          <option :value="null">— not set —</option>
          <option v-for="ch in smtpChannels" :key="ch.id" :value="ch.id">{{ ch.name }}</option>
        </select>
      </div>

      <p v-if="saveMsg" :class="saveMsg.startsWith('Error') ? 'ob-error' : 'ob-success'">{{ saveMsg }}</p>

      <button class="ob-btn-primary" :disabled="saving" @click="save">
        {{ saving ? "Saving…" : "Save Settings" }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import type { SmtpChannel } from "@/api";
import { accountApi, channelsApi, settingsApi } from "@/api";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const timezones = ref<string[]>([]);
const smtpChannels = ref<SmtpChannel[]>([]);
const form = ref({
  timezone: "UTC",
  password_reset_enabled: false,
  recovery_email: "",
  recovery_channel_id: null as number | null,
});
const saving = ref(false);
const saveMsg = ref("");

onMounted(async () => {
  [timezones.value, smtpChannels.value] = await Promise.all([
    settingsApi.timezones(),
    channelsApi.listSmtp(),
  ]);
  const user = await accountApi.me();
  form.value = {
    timezone: user.timezone,
    password_reset_enabled: user.password_reset_enabled,
    recovery_email: user.recovery_email ?? "",
    recovery_channel_id: user.recovery_channel_id ?? null,
  };
});

async function save(): Promise<void> {
  saving.value = true;
  saveMsg.value = "";
  try {
    await accountApi.update({
      timezone: form.value.timezone,
      password_reset_enabled: form.value.password_reset_enabled,
      recovery_email: form.value.recovery_email || undefined,
      recovery_channel_id: form.value.recovery_channel_id ?? undefined,
    } as Parameters<typeof accountApi.update>[0]);
    await auth.fetchMe();
    saveMsg.value = "Settings saved.";
  } catch (e: unknown) {
    saveMsg.value = `Error: ${e instanceof Error ? e.message : "Save failed"}`;
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped lang="scss">
.ob-page-title { font-size: 22px; font-weight: 700; margin: 0 0 20px; }
.ob-section-title { font-size: 15px; font-weight: 600; margin: 0 0 12px; padding-bottom: 8px; border-bottom: 1px solid var(--ob-border); }
.ob-form { display: flex; flex-direction: column; gap: 12px; }
.ob-field { display: flex; flex-direction: column; gap: 4px; label { font-size: 13px; font-weight: 600; } input, select { padding: 7px 10px; border: 1px solid var(--ob-border); border-radius: 6px; font-size: 14px; outline: none; &:focus { border-color: var(--ob-primary); } } }
.ob-checkbox { display: flex; align-items: center; gap: 8px; font-size: 14px; cursor: pointer; }
.ob-btn-primary { background: var(--ob-primary); color: #fff; border: none; border-radius: var(--ob-radius); padding: 8px 16px; font-size: 14px; font-weight: 600; cursor: pointer; align-self: flex-start; &:hover:not(:disabled) { background: var(--ob-primary-dark); } &:disabled { opacity: 0.6; } }
.ob-success { color: var(--ob-success); font-size: 13px; }
.ob-error { color: var(--ob-danger); font-size: 13px; }
</style>
