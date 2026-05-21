<template>
  <div>
    <div class="ob-page-header">
      <h2 class="ob-page-title">Instances</h2>
      <RouterLink :to="{ name: 'instance-detail', params: { id: 'new' } }" class="ob-btn-primary">
        + Add Instance
      </RouterLink>
    </div>

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
        @run-now="runNow(inst)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import type { BackupRun, Instance } from "@/api";
import { backupsApi, instancesApi, jobsApi } from "@/api";
import InstanceCard from "@/components/InstanceCard.vue";

const instances = ref<Instance[]>([]);
const lastRunMap = ref<Record<number, BackupRun | null>>({});
const loading = ref(true);

onMounted(async () => {
  try {
    instances.value = await instancesApi.list();
    const runs = await backupsApi.list({ limit: 200 });
    for (const inst of instances.value) {
      const instRuns = runs.filter((r) => r.instance_id === inst.id);
      lastRunMap.value[inst.id] = instRuns[0] ?? null;
    }
  } finally {
    loading.value = false;
  }
});

async function runNow(inst: Instance): Promise<void> {
  const jobs = await jobsApi.list(inst.id);
  if (jobs.length === 0) {
    alert("No jobs configured for this instance.");
    return;
  }
  await jobsApi.runNow(inst.id, jobs[0].id);
  alert("Backup job enqueued!");
}
</script>

<style scoped lang="scss">
.ob-page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.ob-page-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0;
}

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
</style>
