<template>
  <div>
    <h2 class="ob-page-title">Backups</h2>

    <div class="ob-filters ob-card">
      <label>Filter by instance:</label>
      <select v-model="filterInstanceId">
        <option value="">All instances</option>
        <option v-for="i in instances" :key="i.id" :value="i.id">{{ i.name }}</option>
      </select>
    </div>

    <div class="ob-table-wrap ob-card">
      <table class="ob-table">
        <thead>
          <tr>
            <th>Instance / DB</th>
            <th>Started</th>
            <th>Duration</th>
            <th>Size</th>
            <th>Status</th>
            <th>Verify</th>
            <th>Cloud</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="runs.length === 0">
            <td colspan="8" class="ob-empty-cell">No backup runs yet.</td>
          </tr>
          <tr v-for="run in runs" :key="run.id">
            <td>
              <strong>{{ instanceName(run.instance_id) }}</strong>
              <br /><small class="ob-muted">{{ run.db_name }}</small>
            </td>
            <td class="ob-mono">{{ formatDt(run.started_at) }}</td>
            <td>{{ duration(run) }}</td>
            <td>{{ fileSize(run) }}</td>
            <td><span class="ob-pill" :class="statusClass(run.status)">{{ run.status }}</span></td>
            <td><span class="ob-pill" :class="verifyClass(run.verification_status)">{{ run.verification_status }}</span></td>
            <td>{{ cloudSummary(run) }}</td>
            <td>
              <div class="ob-action-row">
                <a v-if="run.file_path" :href="downloadUrl(run.id)" class="ob-link">↓</a>
                <button class="ob-btn-tiny" @click="verify(run.id)">Re-verify</button>
                <button class="ob-btn-tiny ob-btn-danger-tiny" @click="del(run)">Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="ob-pagination">
      <button :disabled="offset === 0" @click="offset -= 100">← Prev</button>
      <span>{{ offset + 1 }}–{{ offset + runs.length }}</span>
      <button :disabled="runs.length < 100" @click="offset += 100">Next →</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import type { BackupRun, Instance } from "@/api";
import { backupsApi, instancesApi } from "@/api";

const instances = ref<Instance[]>([]);
const runs = ref<BackupRun[]>([]);
const filterInstanceId = ref<number | "">("");
const offset = ref(0);

async function loadRuns(): Promise<void> {
  const params: Record<string, number> = { limit: 100, offset: offset.value };
  if (filterInstanceId.value) params.instance_id = filterInstanceId.value as number;
  runs.value = await backupsApi.list(params);
}

onMounted(async () => {
  instances.value = await instancesApi.list();
  await loadRuns();
});

watch([filterInstanceId, offset], () => loadRuns());

function instanceName(id: number): string {
  return instances.value.find((i) => i.id === id)?.name ?? String(id);
}

function formatDt(iso: string): string {
  return new Date(iso).toLocaleString();
}

function duration(run: BackupRun): string {
  if (!run.finished_at) return "—";
  const ms = new Date(run.finished_at).getTime() - new Date(run.started_at).getTime();
  return `${Math.round(ms / 1000)}s`;
}

function fileSize(run: BackupRun): string {
  if (!run.file_size_bytes) return "—";
  return `${(run.file_size_bytes / 1_048_576).toFixed(1)} MB`;
}

function cloudSummary(run: BackupRun): string {
  if (!run.cloud_sync_status) return "—";
  return Object.entries(run.cloud_sync_status)
    .map(([k, v]) => `${k}: ${v}`)
    .join(", ");
}

function downloadUrl(id: number): string {
  return backupsApi.downloadUrl(id);
}

const statusClass = (s: string) => {
  if (s === "success" || s === "verified") return "ob-pill-success";
  if (s === "failed" || s === "verify_failed") return "ob-pill-danger";
  return "ob-pill-muted";
};

const verifyClass = (s: string) => {
  if (s === "passed") return "ob-pill-success";
  if (s === "failed") return "ob-pill-danger";
  return "ob-pill-muted";
};

async function verify(id: number): Promise<void> {
  await backupsApi.verify(id);
  alert("Re-verification enqueued");
  await loadRuns();
}

async function del(run: BackupRun): Promise<void> {
  const isLast =
    runs.value.filter(
      (r) => r.instance_id === run.instance_id && (r.status === "success" || r.status === "verified")
    ).length <= 1;

  if (isLast) {
    const confirmed = prompt("This is the LAST backup for this instance. Type DELETE to confirm:");
    if (confirmed !== "DELETE") return;
    await backupsApi.delete(run.id, true, "DELETE");
  } else {
    if (!confirm("Delete this backup?")) return;
    await backupsApi.delete(run.id);
  }
  await loadRuns();
}
</script>

<style scoped lang="scss">
.ob-page-title { font-size: 22px; font-weight: 700; margin: 0 0 16px; }
.ob-filters { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; font-size: 14px; select { padding: 6px 10px; border: 1px solid var(--ob-border); border-radius: 6px; font-size: 14px; } }
.ob-table-wrap { overflow-x: auto; padding: 0; }
.ob-table { width: 100%; border-collapse: collapse; font-size: 13px; th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--ob-border); } th { font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ob-text-muted); background: var(--ob-bg); } }
.ob-mono { font-family: monospace; font-size: 12px; }
.ob-muted { color: var(--ob-text-muted); }
.ob-empty-cell { text-align: center; color: var(--ob-text-muted); padding: 32px; }
.ob-action-row { display: flex; align-items: center; gap: 6px; }
.ob-link { font-size: 16px; text-decoration: none; color: var(--ob-accent); }
.ob-btn-tiny { background: none; border: 1px solid var(--ob-border); border-radius: 4px; padding: 2px 8px; font-size: 11px; cursor: pointer; white-space: nowrap; }
.ob-btn-danger-tiny { border-color: var(--ob-danger); color: var(--ob-danger); }
.ob-pagination { display: flex; align-items: center; gap: 12px; margin-top: 16px; font-size: 13px; button { background: none; border: 1px solid var(--ob-border); border-radius: 6px; padding: 4px 12px; cursor: pointer; &:disabled { opacity: 0.4; cursor: not-allowed; } } }
</style>
