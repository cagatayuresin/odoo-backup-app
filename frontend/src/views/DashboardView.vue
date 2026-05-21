<template>
  <div>
    <h2 class="ob-page-title">Dashboard</h2>

    <div class="ob-stat-grid">
      <div class="ob-card ob-stat-card">
        <div class="ob-stat-label">Total Instances</div>
        <div class="ob-stat-value">{{ stats.instances }}</div>
      </div>
      <div class="ob-card ob-stat-card">
        <div class="ob-stat-label">Jobs Enabled</div>
        <div class="ob-stat-value">{{ stats.jobs }}</div>
      </div>
      <div class="ob-card ob-stat-card">
        <div class="ob-stat-label">24h Success Rate</div>
        <div class="ob-stat-value" :class="successRateClass">{{ successRateLabel }}</div>
      </div>
      <div class="ob-card ob-stat-card">
        <div class="ob-stat-label">Next Scheduled Run</div>
        <div class="ob-stat-value ob-stat-small">{{ nextRunLabel }}</div>
      </div>
    </div>

    <div class="ob-row">
      <div style="flex: 1; min-width: 0;">
        <h3 class="ob-section-title">Recent Failures</h3>
        <div v-if="recentFailures.length === 0" class="ob-empty">No failures in recent runs.</div>
        <div v-for="run in recentFailures" :key="run.id" class="ob-card ob-failure-card">
          <div class="ob-failure-header">
            <span class="ob-pill ob-pill-danger">{{ run.status }}</span>
            <span class="ob-failure-db">{{ run.db_name }}</span>
            <span class="ob-failure-time">{{ formatTime(run.started_at) }}</span>
          </div>
          <p v-if="run.error_message" class="ob-failure-error">{{ run.error_message.slice(0, 160) }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import type { BackupRun, Instance, Job } from "@/api";
import { backupsApi, instancesApi, jobsApi } from "@/api";

const instances = ref<Instance[]>([]);
const allJobs = ref<Job[]>([]);
const recentRuns = ref<BackupRun[]>([]);

onMounted(async () => {
  try {
    instances.value = await instancesApi.list();
    const jobPromises = instances.value.map((i) => jobsApi.list(i.id).catch(() => []));
    const results = await Promise.all(jobPromises);
    allJobs.value = results.flat();
    recentRuns.value = await backupsApi.list({ limit: 50 });
  } catch {
    // non-fatal
  }
});

const stats = computed(() => ({
  instances: instances.value.length,
  jobs: allJobs.value.filter((j) => j.enabled).length,
}));

const last24hRuns = computed(() => {
  const cutoff = Date.now() - 24 * 60 * 60 * 1000;
  return recentRuns.value.filter((r) => new Date(r.started_at).getTime() > cutoff);
});

const successRateLabel = computed(() => {
  const runs = last24hRuns.value;
  if (runs.length === 0) return "N/A";
  const ok = runs.filter((r) => r.status === "success" || r.status === "verified").length;
  return `${Math.round((ok / runs.length) * 100)}%`;
});

const successRateClass = computed(() => {
  if (successRateLabel.value === "N/A") return "";
  const pct = parseInt(successRateLabel.value);
  if (pct === 100) return "ob-stat-green";
  if (pct >= 80) return "ob-stat-yellow";
  return "ob-stat-red";
});

const nextRunLabel = computed(() => {
  const upcoming = allJobs.value
    .filter((j) => j.enabled && j.next_run_at)
    .map((j) => new Date(j.next_run_at!).getTime())
    .sort((a, b) => a - b);
  if (upcoming.length === 0) return "No jobs scheduled";
  const ms = upcoming[0] - Date.now();
  if (ms < 60000) return "< 1 minute";
  const minutes = Math.round(ms / 60000);
  if (minutes < 60) return `${minutes} min`;
  return `${Math.round(minutes / 60)}h`;
});

const recentFailures = computed(() =>
  recentRuns.value
    .filter((r) => r.status === "failed" || r.status === "verify_failed")
    .slice(0, 5)
);

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}
</script>

<style scoped lang="scss">
.ob-page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--ob-text);
  margin: 0 0 20px;
}

.ob-stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.ob-stat-card {
  text-align: center;
}

.ob-stat-label {
  font-size: 12px;
  color: var(--ob-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 8px;
}

.ob-stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--ob-text);

  &.ob-stat-small { font-size: 18px; }
  &.ob-stat-green { color: var(--ob-success); }
  &.ob-stat-yellow { color: var(--ob-warning); }
  &.ob-stat-red { color: var(--ob-danger); }
}

.ob-section-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 12px;
}

.ob-failure-card {
  margin-bottom: 8px;
}

.ob-failure-header {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.ob-failure-db {
  font-weight: 600;
  font-size: 14px;
}

.ob-failure-time {
  margin-left: auto;
  font-size: 12px;
  color: var(--ob-text-muted);
}

.ob-failure-error {
  margin: 8px 0 0;
  font-size: 12px;
  font-family: monospace;
  color: var(--ob-danger);
}

.ob-empty {
  color: var(--ob-text-muted);
  font-size: 14px;
  padding: 16px;
  text-align: center;
}

.ob-row {
  display: flex;
  gap: 20px;
}
</style>
