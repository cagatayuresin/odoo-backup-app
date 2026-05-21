<template>
  <div>
    <div class="ob-page-header">
      <h2 class="ob-page-title">{{ isNew ? "New Job" : "Edit Job" }}</h2>
      <RouterLink :to="{ name: 'instance-detail', params: { id: props.instanceId } }" class="ob-btn-back">
        ← Back to Instance
      </RouterLink>
    </div>

    <form @submit.prevent="save" class="ob-card ob-form">
      <div class="ob-field">
        <label>Job Name</label>
        <input v-model="form.name" required placeholder="Daily Backup" />
      </div>

      <div class="ob-field">
        <label>Schedule</label>
        <CronBuilder v-model="form.cron_expression" />
      </div>

      <label class="ob-checkbox">
        <input v-model="form.enabled" type="checkbox" />
        Job enabled
      </label>

      <p v-if="error" class="ob-error">{{ error }}</p>

      <div class="ob-form-actions">
        <button type="submit" class="ob-btn-primary" :disabled="saving">
          {{ saving ? "Saving…" : isNew ? "Create Job" : "Save Changes" }}
        </button>
        <button v-if="!isNew" type="button" class="ob-btn-danger" @click="deleteJob">Delete Job</button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { jobsApi } from "@/api";
import CronBuilder from "@/components/CronBuilder.vue";

const props = defineProps<{
  instanceId: string;
  jobId?: string;
}>();

const router = useRouter();
const isNew = computed(() => !props.jobId || props.jobId === "new");
const instanceIdNum = computed(() => parseInt(props.instanceId));

const form = ref({
  name: "",
  cron_expression: "0 2 * * *",
  enabled: true,
});

const saving = ref(false);
const error = ref("");

onMounted(async () => {
  if (!isNew.value && props.jobId) {
    const job = await jobsApi.get(instanceIdNum.value, parseInt(props.jobId));
    form.value = {
      name: job.name,
      cron_expression: job.cron_expression,
      enabled: job.enabled,
    };
  }
});

async function save(): Promise<void> {
  error.value = "";
  saving.value = true;
  try {
    if (isNew.value) {
      await jobsApi.create(instanceIdNum.value, form.value);
    } else {
      await jobsApi.update(instanceIdNum.value, parseInt(props.jobId!), form.value);
    }
    router.push({ name: "instance-detail", params: { id: props.instanceId } });
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "Save failed";
  } finally {
    saving.value = false;
  }
}

async function deleteJob(): Promise<void> {
  if (!confirm("Delete this job?")) return;
  await jobsApi.delete(instanceIdNum.value, parseInt(props.jobId!));
  router.push({ name: "instance-detail", params: { id: props.instanceId } });
}
</script>

<style scoped lang="scss">
.ob-page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.ob-page-title { font-size: 22px; font-weight: 700; margin: 0; }
.ob-btn-back { color: var(--ob-text-muted); font-size: 13px; text-decoration: none; &:hover { color: var(--ob-text); } }
.ob-form { display: flex; flex-direction: column; gap: 16px; }
.ob-field { display: flex; flex-direction: column; gap: 6px; label { font-size: 13px; font-weight: 600; } input { padding: 8px 12px; border: 1px solid var(--ob-border); border-radius: var(--ob-radius); font-size: 14px; outline: none; &:focus { border-color: var(--ob-primary); } } }
.ob-checkbox { display: flex; align-items: center; gap: 8px; font-size: 14px; cursor: pointer; }
.ob-form-actions { display: flex; gap: 10px; align-items: center; }
.ob-btn-primary { background: var(--ob-primary); color: #fff; border: none; border-radius: var(--ob-radius); padding: 8px 18px; font-size: 14px; font-weight: 600; cursor: pointer; &:hover:not(:disabled) { background: var(--ob-primary-dark); } &:disabled { opacity: 0.6; } }
.ob-btn-danger { background: none; border: 1px solid var(--ob-danger); border-radius: var(--ob-radius); padding: 8px 18px; font-size: 14px; color: var(--ob-danger); cursor: pointer; &:hover { background: #fdf2f2; } }
.ob-error { color: var(--ob-danger); font-size: 13px; }
</style>
