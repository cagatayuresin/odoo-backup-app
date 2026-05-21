<template>
  <div class="ob-card ob-instance-card" :class="{ 'is-running': running }">
    <!-- Progress bar -->
    <div v-if="running" class="ob-progress-bar">
      <div class="ob-progress-fill" />
    </div>

    <div class="ob-instance-header">
      <div class="ob-instance-name-row">
        <span class="ob-instance-name">{{ instance.name }}</span>
        <span class="ob-instance-slug">{{ instance.slug }}</span>
      </div>
      <span class="ob-pill" :class="methodClass" :title="methodTooltip">
        {{ instance.backup_method === 'odoo_endpoint' ? '☁' : '🗄' }}
        {{ instance.backup_method === 'odoo_endpoint' ? 'Odoo API' : 'pg_dump' }}
      </span>
    </div>

    <div class="ob-instance-url">
      <span class="ob-scheme-badge">{{ instance.parsed_scheme }}</span>
      <a :href="instance.raw_url" target="_blank" class="ob-instance-host">
        {{ instance.parsed_host }}{{ instance.parsed_port !== defaultPort ? ':' + instance.parsed_port : '' }}
      </a>
    </div>

    <div class="ob-instance-meta">
      <span v-if="running" class="ob-running-label">
        Backup running…
      </span>
      <span v-else-if="lastRun" class="ob-instance-last">
        Last run:
        <span class="ob-pill" :class="statusClass">{{ lastRun.status }}</span>
        {{ timeAgo(lastRun.started_at) }}
      </span>
      <span v-else class="ob-instance-last ob-text-muted">No backups yet</span>
    </div>

    <div class="ob-instance-actions">
      <RouterLink :to="{ name: 'instance-detail', params: { id: instance.id } }" class="ob-btn-sm">
        Edit
      </RouterLink>
      <button class="ob-btn-sm" :disabled="running" @click="$emit('run-now')">
        {{ running ? 'Running…' : 'Run now' }}
      </button>
      <RouterLink :to="{ name: 'backups', query: { instance_id: instance.id } }" class="ob-btn-sm">
        Backups
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import type { BackupRun, Instance } from "@/api";

const props = defineProps<{
  instance: Instance;
  lastRun?: BackupRun | null;
  running?: boolean;
}>();

defineEmits<{
  (e: "run-now"): void;
}>();

const defaultPort = computed(() =>
  props.instance.parsed_scheme === "https" ? 443 : 80
);

const methodClass = computed(() =>
  props.instance.backup_method === "odoo_endpoint" ? "ob-pill-info" : "ob-pill-muted"
);

const methodTooltip = computed(() =>
  props.instance.backup_method === "odoo_endpoint"
    ? "Uses Odoo /web/database/backup endpoint"
    : "Uses direct pg_dump"
);

const statusClass = computed(() => {
  const s = props.lastRun?.status;
  if (s === "success" || s === "verified") return "ob-pill-success";
  if (s === "failed" || s === "verify_failed") return "ob-pill-danger";
  if (s === "running") return "ob-pill-info";
  return "ob-pill-muted";
});

function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(ms / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}
</script>

<style scoped lang="scss">
.ob-instance-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
  position: relative;
  transition: box-shadow 0.2s;

  &.is-running {
    border-color: var(--ob-accent);
    box-shadow: 0 0 0 1px var(--ob-accent);
  }
}

// Animated indeterminate progress bar
.ob-progress-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: #e5f6f7;
  overflow: hidden;
}

.ob-progress-fill {
  height: 100%;
  width: 40%;
  background: var(--ob-accent);
  border-radius: 2px;
  animation: ob-slide 1.4s ease-in-out infinite;
}

@keyframes ob-slide {
  0%   { transform: translateX(-150%); }
  100% { transform: translateX(350%); }
}

.ob-instance-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.ob-instance-name-row {
  display: flex;
  flex-direction: column;
}

.ob-instance-name { font-weight: 600; font-size: 15px; }
.ob-instance-slug { font-size: 12px; color: var(--ob-text-muted); font-family: monospace; }

.ob-instance-url {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--ob-text-muted);
}

.ob-scheme-badge {
  background: #e9ecef;
  border-radius: 4px;
  padding: 1px 6px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.ob-instance-host {
  color: var(--ob-text-muted);
  text-decoration: none;
  &:hover { color: var(--ob-accent); text-decoration: underline; }
}

.ob-instance-meta { font-size: 13px; }

.ob-instance-last {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.ob-running-label {
  color: var(--ob-accent);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}

.ob-text-muted { color: var(--ob-text-muted); }

.ob-instance-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.ob-btn-sm {
  background: none;
  border: 1px solid var(--ob-border);
  border-radius: 6px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  color: var(--ob-text);
  transition: background 0.1s;
  &:hover:not(:disabled) { background: var(--ob-bg); }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}
</style>
