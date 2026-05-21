<template>
  <div class="ob-cron-builder">
    <!-- Mode tabs -->
    <div class="ob-cron-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="ob-cron-tab"
        :class="{ active: activeTab === tab.id }"
        type="button"
        @click="setTab(tab.id)"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Visual builder -->
    <div v-if="activeTab !== 'custom'" class="ob-cron-visual">
      <div v-if="activeTab === 'hourly'" class="ob-cron-row">
        <label>Every hour at minute</label>
        <input v-model.number="minute" type="number" min="0" max="59" />
      </div>

      <div v-if="activeTab === 'daily'" class="ob-cron-row">
        <label>Every day at</label>
        <input v-model.number="hour" type="number" min="0" max="23" />
        <span>:</span>
        <input v-model.number="minute" type="number" min="0" max="59" />
      </div>

      <div v-if="activeTab === 'weekly'" class="ob-cron-row ob-cron-col">
        <label>Days of week</label>
        <div class="ob-dow-grid">
          <label v-for="d in daysOfWeek" :key="d.value" class="ob-dow-label">
            <input v-model="selectedDays" type="checkbox" :value="d.value" />
            {{ d.label }}
          </label>
        </div>
        <div class="ob-cron-row" style="margin-top: 8px">
          <label>At</label>
          <input v-model.number="hour" type="number" min="0" max="23" />
          <span>:</span>
          <input v-model.number="minute" type="number" min="0" max="59" />
        </div>
      </div>

      <div v-if="activeTab === 'monthly'" class="ob-cron-row">
        <label>Day of month</label>
        <select v-model="dayOfMonth">
          <option v-for="n in 31" :key="n" :value="n">{{ n }}</option>
          <option value="L">Last day</option>
        </select>
        <label>at</label>
        <input v-model.number="hour" type="number" min="0" max="23" />
        <span>:</span>
        <input v-model.number="minute" type="number" min="0" max="59" />
      </div>
    </div>

    <!-- Raw cron input -->
    <div class="ob-cron-raw">
      <label>Cron expression</label>
      <input
        v-model="rawExpr"
        type="text"
        placeholder="0 2 * * *"
        class="ob-cron-input"
        @input="onRawInput"
      />
      <p v-if="validationError" class="ob-cron-error">{{ validationError }}</p>
    </div>

    <!-- Next runs preview -->
    <div v-if="nextRuns.length > 0" class="ob-cron-preview">
      <p class="ob-cron-preview-label">Next {{ nextRuns.length }} runs:</p>
      <ul>
        <li v-for="(run, i) in nextRuns" :key="i">{{ formatPreview(run) }}</li>
      </ul>
    </div>
    <p v-else-if="loadingPreview" class="ob-cron-preview-label">Loading preview…</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useAuthStore } from "@/stores/auth";
import { settingsApi } from "@/api";

const props = defineProps<{
  modelValue: string;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", val: string): void;
}>();

const auth = useAuthStore();
const tz = computed(() => auth.user?.timezone ?? "UTC");

const tabs = [
  { id: "hourly", label: "Hourly" },
  { id: "daily", label: "Daily" },
  { id: "weekly", label: "Weekly" },
  { id: "monthly", label: "Monthly" },
  { id: "custom", label: "Custom" },
];

const daysOfWeek = [
  { label: "Mon", value: 1 },
  { label: "Tue", value: 2 },
  { label: "Wed", value: 3 },
  { label: "Thu", value: 4 },
  { label: "Fri", value: 5 },
  { label: "Sat", value: 6 },
  { label: "Sun", value: 0 },
];

const activeTab = ref("daily");
const minute = ref(0);
const hour = ref(2);
const selectedDays = ref<number[]>([1, 2, 3, 4, 5]);
const dayOfMonth = ref<number | "L">(1);
const rawExpr = ref(props.modelValue || "0 2 * * *");
const validationError = ref("");
const nextRuns = ref<string[]>([]);
const loadingPreview = ref(false);

// Build the cron expression from visual state
const builtExpr = computed(() => {
  if (activeTab.value === "hourly") return `${minute.value} * * * *`;
  if (activeTab.value === "daily") return `${minute.value} ${hour.value} * * *`;
  if (activeTab.value === "weekly") {
    const days = selectedDays.value.sort().join(",") || "*";
    return `${minute.value} ${hour.value} * * ${days}`;
  }
  if (activeTab.value === "monthly") {
    return `${minute.value} ${hour.value} ${dayOfMonth.value} * *`;
  }
  return rawExpr.value;
});

// Sync built expression → raw input and emit
watch(builtExpr, (val) => {
  if (activeTab.value !== "custom") {
    rawExpr.value = val;
    emit("update:modelValue", val);
    refreshPreview(val);
  }
});

function setTab(id: string): void {
  activeTab.value = id;
  if (id !== "custom") {
    emit("update:modelValue", builtExpr.value);
  }
}

function onRawInput(): void {
  emit("update:modelValue", rawExpr.value);
  refreshPreview(rawExpr.value);
}

async function refreshPreview(expr: string): Promise<void> {
  if (!expr.trim()) return;
  loadingPreview.value = true;
  validationError.value = "";
  try {
    const result = await settingsApi.cronPreview(expr, tz.value, 5);
    nextRuns.value = result.next_runs;
  } catch (e: unknown) {
    validationError.value = e instanceof Error ? e.message : "Invalid expression";
    nextRuns.value = [];
  } finally {
    loadingPreview.value = false;
  }
}

function formatPreview(iso: string): string {
  return new Date(iso).toLocaleString();
}

onMounted(() => {
  refreshPreview(rawExpr.value);
});
</script>

<style scoped lang="scss">
.ob-cron-builder {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ob-cron-tabs {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.ob-cron-tab {
  padding: 6px 14px;
  border: 1px solid var(--ob-border);
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  background: none;
  color: var(--ob-text-muted);
  transition: all 0.1s;

  &.active {
    background: var(--ob-primary);
    color: #fff;
    border-color: var(--ob-primary);
  }
}

.ob-cron-visual {
  padding: 12px;
  background: var(--ob-bg);
  border-radius: var(--ob-radius);
  border: 1px solid var(--ob-border);
}

.ob-cron-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  flex-wrap: wrap;

  &.ob-cron-col { flex-direction: column; align-items: flex-start; }
}

.ob-cron-row input, .ob-cron-row select {
  padding: 4px 8px;
  border: 1px solid var(--ob-border);
  border-radius: 4px;
  font-size: 14px;
  width: 70px;
}

.ob-dow-grid {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.ob-dow-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  cursor: pointer;
}

label { font-size: 13px; font-weight: 500; }

.ob-cron-raw {
  label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 4px; }
}

.ob-cron-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--ob-border);
  border-radius: var(--ob-radius);
  font-family: monospace;
  font-size: 14px;
  outline: none;

  &:focus { border-color: var(--ob-primary); }
}

.ob-cron-error { color: var(--ob-danger); font-size: 12px; margin: 4px 0 0; }

.ob-cron-preview {
  background: var(--ob-bg);
  border: 1px solid var(--ob-border);
  border-radius: var(--ob-radius);
  padding: 10px 12px;
  font-size: 13px;

  ul { margin: 4px 0 0; padding-left: 16px; }
  li { margin-bottom: 2px; font-family: monospace; }
}

.ob-cron-preview-label { font-size: 12px; color: var(--ob-text-muted); margin: 0 0 4px; }
</style>
