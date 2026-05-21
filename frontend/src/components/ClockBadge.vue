<template>
  <div class="clock-badge" :title="tooltip">
    <span class="clock-time">{{ currentTime }}</span>
    <span class="clock-offset">{{ offsetLabel }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const now = ref(new Date());
let timer: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  timer = setInterval(() => {
    now.value = new Date();
  }, 1000);
});

onUnmounted(() => {
  if (timer !== null) clearInterval(timer);
});

const tz = computed(() => auth.user?.timezone ?? "UTC");

const currentTime = computed(() => {
  return now.value.toLocaleTimeString("en-US", {
    timeZone: tz.value,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
});

const offsetLabel = computed(() => {
  try {
    const formatter = new Intl.DateTimeFormat("en", {
      timeZone: tz.value,
      timeZoneName: "shortOffset",
    });
    const parts = formatter.formatToParts(now.value);
    return parts.find((p) => p.type === "timeZoneName")?.value ?? tz.value;
  } catch {
    return tz.value;
  }
});

const tooltip = computed(
  () => `All schedules are stored in UTC; preview times shown in your timezone (${tz.value}).`
);
</script>

<style scoped lang="scss">
.clock-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  cursor: default;
}

.clock-time {
  font-weight: 600;
  color: var(--ob-text);
  font-variant-numeric: tabular-nums;
}

.clock-offset {
  background: #f3f0f5;
  color: var(--ob-primary);
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 11px;
  font-weight: 600;
}
</style>
