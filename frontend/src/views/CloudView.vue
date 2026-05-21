<template>
  <div>
    <h2 class="ob-page-title">Cloud Sync</h2>
    <p class="ob-desc">
      Connect cloud storage accounts here, then bind them to individual instances on each
      Instance Detail page.
    </p>

    <button class="ob-btn-primary ob-mb" @click="showForm = !showForm">
      {{ showForm ? "Cancel" : "+ Add Cloud Account" }}
    </button>

    <form v-if="showForm" class="ob-card ob-form" @submit.prevent="create">
      <div class="ob-field">
        <label>Provider</label>
        <select v-model="form.provider">
          <option value="gdrive">Google Drive</option>
          <option value="dropbox">Dropbox</option>
          <option value="onedrive">OneDrive</option>
        </select>
      </div>
      <div class="ob-field"><label>Account Name</label><input v-model="form.name" required placeholder="My Drive" /></div>
      <div class="ob-field">
        <label>Credentials (JSON)</label>
        <textarea v-model="credsText" rows="6" placeholder='{"access_token": "..."}' required />
        <p class="ob-hint">
          Paste the JSON credentials for this provider as a JSON object.
          Google Drive: use OAuth token JSON. Dropbox: use access_token. OneDrive: use MSAL token JSON.
        </p>
      </div>
      <button type="submit" class="ob-btn-primary">Save Account</button>
      <p v-if="error" class="ob-error">{{ error }}</p>
    </form>

    <div v-for="acc in accounts" :key="acc.id" class="ob-card ob-account-card">
      <div class="ob-account-info">
        <span class="ob-account-provider" :class="`ob-provider-${acc.provider}`">
          {{ providerLabel(acc.provider) }}
        </span>
        <span class="ob-account-name">{{ acc.name }}</span>
        <span class="ob-pill" :class="acc.enabled ? 'ob-pill-success' : 'ob-pill-muted'">
          {{ acc.enabled ? "enabled" : "disabled" }}
        </span>
      </div>
      <div class="ob-account-actions">
        <button class="ob-btn-sm ob-btn-danger-sm" @click="del(acc.id)">Delete</button>
      </div>
    </div>

    <p v-if="accounts.length === 0 && !showForm" class="ob-empty">
      No cloud accounts configured. Add one to start syncing backups to the cloud.
    </p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import type { CloudAccount } from "@/api";
import { cloudApi } from "@/api";

const accounts = ref<CloudAccount[]>([]);
const showForm = ref(false);
const form = ref({ provider: "gdrive", name: "" });
const credsText = ref("");
const error = ref("");

onMounted(async () => {
  accounts.value = await cloudApi.listAccounts();
});

function providerLabel(p: string): string {
  return { gdrive: "Google Drive", dropbox: "Dropbox", onedrive: "OneDrive" }[p] ?? p;
}

async function create(): Promise<void> {
  error.value = "";
  try {
    const creds: Record<string, string> = JSON.parse(credsText.value);
    await cloudApi.createAccount({ ...form.value, credentials: creds, enabled: true });
    accounts.value = await cloudApi.listAccounts();
    showForm.value = false;
    credsText.value = "";
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "Failed to create account";
  }
}

async function del(id: number): Promise<void> {
  if (!confirm("Delete this cloud account?")) return;
  await cloudApi.deleteAccount(id);
  accounts.value = accounts.value.filter((a) => a.id !== id);
}
</script>

<style scoped lang="scss">
.ob-page-title { font-size: 22px; font-weight: 700; margin: 0 0 8px; }
.ob-desc { color: var(--ob-text-muted); font-size: 14px; margin: 0 0 16px; }
.ob-btn-primary { background: var(--ob-primary); color: #fff; border: none; border-radius: var(--ob-radius); padding: 8px 16px; font-size: 14px; font-weight: 600; cursor: pointer; &:hover { background: var(--ob-primary-dark); } }
.ob-mb { margin-bottom: 16px; }
.ob-form { display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px; }
.ob-field { display: flex; flex-direction: column; gap: 4px; label { font-size: 13px; font-weight: 600; } input, select, textarea { padding: 7px 10px; border: 1px solid var(--ob-border); border-radius: 6px; font-size: 14px; outline: none; &:focus { border-color: var(--ob-primary); } } textarea { font-family: monospace; resize: vertical; } }
.ob-hint { font-size: 11px; color: var(--ob-text-muted); margin: 2px 0 0; a { color: var(--ob-accent); } }
.ob-error { color: var(--ob-danger); font-size: 13px; }
.ob-account-card { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; flex-wrap: wrap; gap: 10px; }
.ob-account-info { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.ob-account-provider { font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 4px; background: #e9ecef; }
.ob-account-name { font-weight: 600; font-size: 14px; }
.ob-account-actions { display: flex; gap: 8px; }
.ob-btn-sm { background: none; border: 1px solid var(--ob-border); border-radius: 6px; padding: 4px 12px; font-size: 12px; cursor: pointer; }
.ob-btn-danger-sm { border-color: var(--ob-danger); color: var(--ob-danger); }
.ob-empty { color: var(--ob-text-muted); font-size: 14px; text-align: center; padding: 32px; }
</style>
