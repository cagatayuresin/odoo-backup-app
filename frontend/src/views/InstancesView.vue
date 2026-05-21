<template>
  <div>
    <div class="ob-page-header">
      <h2 class="ob-page-title">Instances</h2>
      <RouterLink :to="{ name: 'instance-detail', params: { id: 'new' } }" class="ob-btn-primary">
        + Add Instance
      </RouterLink>
    </div>

    <p v-if="runMsg" :class="runMsg.ok ? 'ob-msg-ok' : 'ob-msg-err'" style="margin-bottom: 12px;">
      {{ runMsg.text }}
    </p>

    <div v-if="loading" class="ob-empty">Loading…</div>
    <div v-else-if="instances.length === 0" class="ob-empty">
      No instances yet. Add your first Odoo instance to get started.
    </div>
    <div v-else class="ob-card-grid">
      <InstanceCard
        v-for="inst in instances"
        :key="inst.id"
        :instance="inst"
        :last-run="lastRunMap[inst.id] ?? null"
        :running="runningSet.has(inst.id)"
        @run-now="runNow(inst)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { RouterLink } from "vue-router";
import type { BackupRun, Instance } from "@/api";
import { backupsApi, instancesApi, jobsApi } from "@/api";
import InstanceCard from "@/components/InstanceCard.vue";

const instances = ref<Instance[]>([]);
const lastRunMap = ref<Record<number, BackupRun | null>>({});
const runningSet = ref<Set<number>>(new Set());
const loading = ref(true);
const runMsg = ref<{ text: string; ok: boolean } | null>(null);
let pollTimer: ReturnType<typeof setInterval> | null = null;

async function loadData(): Promise<void> {
  const runs = await backupsApi.list({ limit: 200 });
  const newRunning = new Set<number>();
  for (const inst of instances.value) {
    const instRuns = runs.filter((r) => r.instance_id === inst.id);
    lastRunMap.value[inst.id] = instRuns[0] ?? null;
    if (instRuns.some((r) => r.status === "running")) newRunning.add(inst.id);
  }
  runningSet.value = newRunning;
}

onMounted(async () => {
  try {
    instances.value = await instancesApi.list();
    await loadData();
  } finally {
    loading.value = false;
  }
  pollTimer = setInterval(loadData, 4000);
});

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
});

async function runNow(inst: Instance): Promise<void> {
  runMsg.value = null;
  try {
    const jobs = await jobsApi.list(inst.id);
    if (jobs.length === 0) {
      runMsg.value = { text: `No jobs configured for "${inst.name}".`, ok: false };
      return;
    }
    await jobsApi.runNow(inst.id, jobs[0].id);
    runMsg.value = { text: `Backup job enqueued for "${inst.name}".`, ok: true };
    runningSet.value = new Set([...runningSet.value, inst.id]);
  } catch (e: unknown) {
    runMsg.value = { text: e instanceof Error ? e.message : "Failed to enqueue job.", ok: false };
  }
}
</script>

<style scoped lang="scss">
.ob-page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.ob-page-title { font-size: 22px; font-weight: 700; margin: 0; }

.ob-btn-primary {
  background: var(--ob-primary);
  color: #fff;
  border: none;
  border-radius: var(--ob-radius);
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: background 0.15s;
  &:hover { background: var(--ob-primary-dark); }
}

.ob-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.ob-empty {
  text-align: center;
  color: var(--ob-text-muted);
  padding: 48px 16px;
  font-size: 14px;
}

.ob-msg-ok { font-size: 13px; color: var(--ob-success); }
.ob-msg-err { font-size: 13px; color: var(--ob-danger); }
</style>
