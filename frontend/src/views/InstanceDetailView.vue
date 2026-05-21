<template>
  <div>
    <div class="ob-page-header">
      <h2 class="ob-page-title">{{ isNew ? "Add Instance" : form.name }}</h2>
      <RouterLink :to="{ name: 'instances' }" class="ob-btn-back">← Instances</RouterLink>
    </div>

    <form @submit.prevent="save" class="ob-card ob-form">
      <div class="ob-form-section">
        <h3>Basic Information</h3>
        <div class="ob-field">
          <label>Instance Name</label>
          <input v-model="form.name" required placeholder="My Odoo Production" />
        </div>
        <div class="ob-field">
          <label>URL / Host</label>
          <input v-model="form.raw_url" required placeholder="https://erp.mycompany.com" />
          <p class="ob-field-hint">Enter hostname, IP, or full URL — port and scheme will be detected automatically.</p>
        </div>
      </div>

      <div class="ob-form-section">
        <h3>Backup Method</h3>
        <div class="ob-radio-group">
          <label>
            <input v-model="form.backup_method" type="radio" value="odoo_endpoint" />
            Odoo Endpoint — uses <code>/web/database/backup</code>, requires master password
          </label>
          <label>
            <input v-model="form.backup_method" type="radio" value="pg_dump" />
            pg_dump — direct database dump, requires PostgreSQL credentials
          </label>
        </div>

        <div v-if="form.backup_method === 'odoo_endpoint'" class="ob-field">
          <label>Master Password</label>
          <input v-model="form.master_password" type="password" placeholder="Leave blank to keep existing" />
        </div>

        <template v-if="form.backup_method === 'pg_dump'">
          <div class="ob-form-row">
            <div class="ob-field">
              <label>DB Host</label>
              <input v-model="form.db_host" placeholder="localhost" required />
            </div>
            <div class="ob-field ob-field-sm">
              <label>Port</label>
              <input v-model.number="form.db_port" type="number" placeholder="5432" />
            </div>
          </div>
          <div class="ob-form-row">
            <div class="ob-field">
              <label>DB User</label>
              <input v-model="form.db_user" placeholder="odoo" required />
            </div>
            <div class="ob-field">
              <label>DB Password</label>
              <input v-model="form.db_password" type="password" placeholder="Leave blank to keep existing" />
            </div>
          </div>
          <div class="ob-field">
            <label>Filestore Path (optional)</label>
            <input v-model="form.filestore_path" placeholder="/var/lib/odoo/filestore" />
          </div>
          <label class="ob-checkbox">
            <input v-model="form.include_filestore" type="checkbox" />
            Include filestore in backup archive
          </label>
        </template>
      </div>

      <div class="ob-form-section">
        <h3>Database Selection</h3>
        <div class="ob-radio-group">
          <label><input v-model="form.db_selection_mode" type="radio" value="single" /> Single database</label>
          <label><input v-model="form.db_selection_mode" type="radio" value="selected" /> Selected databases</label>
          <label><input v-model="form.db_selection_mode" type="radio" value="all" /> All databases (auto-discover)</label>
        </div>
        <div v-if="form.db_selection_mode !== 'all'" class="ob-field">
          <label>Database name(s) — one per line</label>
          <textarea v-model="dbNamesText" rows="3" placeholder="mydb"></textarea>
        </div>
      </div>

      <div class="ob-form-section">
        <h3>Retention</h3>
        <div class="ob-form-row">
          <div class="ob-field">
            <label>Mode</label>
            <select v-model="form.retention_mode">
              <option value="keep_last_n">Keep last N backups</option>
              <option value="older_than_days">Delete older than N days</option>
            </select>
          </div>
          <div class="ob-field ob-field-sm">
            <label>N</label>
            <input v-model.number="form.retention_value" type="number" min="1" />
          </div>
        </div>
      </div>

      <div class="ob-form-section">
        <label class="ob-checkbox">
          <input v-model="form.notifications_enabled" type="checkbox" />
          Enable notifications for this instance
        </label>
      </div>

      <p v-if="error" class="ob-error">{{ error }}</p>
      <p v-if="successMsg" class="ob-success">{{ successMsg }}</p>

      <div class="ob-form-actions">
        <button type="submit" class="ob-btn-primary" :disabled="saving">
          {{ saving ? "Saving…" : isNew ? "Create Instance" : "Save Changes" }}
        </button>
        <button v-if="!isNew" type="button" class="ob-btn-secondary" @click="testConnection">
          Test Connection
        </button>
        <button
          v-if="!isNew"
          type="button"
          class="ob-btn-danger"
          @click="deleteInstance"
        >
          Delete
        </button>
      </div>
    </form>

    <!-- Jobs section for existing instances -->
    <div v-if="!isNew" class="ob-section ob-card">
      <div class="ob-section-header">
        <h3>Scheduled Jobs</h3>
        <RouterLink
          :to="{ name: 'job-editor', params: { instanceId: instanceId, jobId: 'new' } }"
          class="ob-btn-primary ob-btn-sm-primary"
        >
          + Add Job
        </RouterLink>
      </div>
      <div v-if="jobs.length === 0" class="ob-empty">No jobs configured yet.</div>
      <div v-for="job in jobs" :key="job.id" class="ob-job-row">
        <div>
          <span class="ob-job-name">{{ job.name }}</span>
          <code class="ob-cron-code">{{ job.cron_expression }}</code>
        </div>
        <div class="ob-job-actions">
          <span class="ob-pill" :class="job.enabled ? 'ob-pill-success' : 'ob-pill-muted'">
            {{ job.enabled ? "enabled" : "disabled" }}
          </span>
          <RouterLink
            :to="{ name: 'job-editor', params: { instanceId: instanceId, jobId: job.id } }"
            class="ob-btn-sm"
          >Edit</RouterLink>
          <button class="ob-btn-sm" @click="runJob(job.id)">Run now</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import type { Job } from "@/api";
import { instancesApi, jobsApi } from "@/api";

const props = defineProps<{
  id: string;
}>();

const router = useRouter();
const isNew = computed(() => props.id === "new");
const instanceId = computed(() => parseInt(props.id));

const form = ref({
  name: "",
  raw_url: "",
  backup_method: "odoo_endpoint" as "odoo_endpoint" | "pg_dump",
  master_password: "",
  db_host: "",
  db_port: 5432,
  db_user: "",
  db_password: "",
  filestore_path: "",
  include_filestore: false,
  db_selection_mode: "single" as "single" | "selected" | "all",
  db_names: [] as string[],
  retention_mode: "keep_last_n" as "keep_last_n" | "older_than_days",
  retention_value: 7,
  notifications_enabled: true,
});

const dbNamesText = computed({
  get: () => form.value.db_names.join("\n"),
  set: (v: string) => {
    form.value.db_names = v.split("\n").map((s) => s.trim()).filter(Boolean);
  },
});

const jobs = ref<Job[]>([]);
const saving = ref(false);
const error = ref("");
const successMsg = ref("");

onMounted(async () => {
  if (!isNew.value) {
    const inst = await instancesApi.get(instanceId.value);
    Object.assign(form.value, inst, {
      db_names: inst.db_names ?? [],
      master_password: "",
      db_password: "",
    });
    jobs.value = await jobsApi.list(instanceId.value);
  }
});

async function save(): Promise<void> {
  error.value = "";
  saving.value = true;
  try {
    const payload = {
      ...form.value,
      db_names: form.value.db_selection_mode !== "all" ? form.value.db_names : [],
      master_password: form.value.master_password || undefined,
      db_password: form.value.db_password || undefined,
    };

    if (isNew.value) {
      const created = await instancesApi.create(payload);
      router.push({ name: "instance-detail", params: { id: created.id } });
    } else {
      await instancesApi.update(instanceId.value, payload);
      successMsg.value = "Saved!";
      setTimeout(() => { successMsg.value = ""; }, 3000);
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "Save failed";
  } finally {
    saving.value = false;
  }
}

async function testConnection(): Promise<void> {
  try {
    const result = await instancesApi.testConnection(instanceId.value);
    alert(`Connection test: ${result.status}\n${result.detail ?? ""}`);
  } catch (e: unknown) {
    alert(`Connection failed: ${e instanceof Error ? e.message : "Unknown error"}`);
  }
}

async function deleteInstance(): Promise<void> {
  if (!confirm("Delete this instance and all its backup records? This cannot be undone.")) return;
  await instancesApi.delete(instanceId.value);
  router.push({ name: "instances" });
}

async function runJob(jobId: number): Promise<void> {
  await jobsApi.runNow(instanceId.value, jobId);
  alert("Job enqueued!");
}
</script>

<style scoped lang="scss">
.ob-page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.ob-page-title { font-size: 22px; font-weight: 700; margin: 0; }
.ob-btn-back { color: var(--ob-text-muted); font-size: 13px; text-decoration: none; &:hover { color: var(--ob-text); } }
.ob-form { display: flex; flex-direction: column; gap: 24px; }
.ob-form-section { display: flex; flex-direction: column; gap: 12px; h3 { font-size: 15px; font-weight: 600; margin: 0 0 4px; border-bottom: 1px solid var(--ob-border); padding-bottom: 8px; } }
.ob-form-row { display: flex; gap: 12px; flex-wrap: wrap; }
.ob-field { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 200px; &.ob-field-sm { flex: 0 0 100px; min-width: 80px; } label { font-size: 13px; font-weight: 600; } input, select, textarea { padding: 8px 10px; border: 1px solid var(--ob-border); border-radius: var(--ob-radius); font-size: 14px; outline: none; &:focus { border-color: var(--ob-primary); } } textarea { resize: vertical; font-family: monospace; } }
.ob-field-hint { font-size: 11px; color: var(--ob-text-muted); margin: 0; }
.ob-radio-group { display: flex; flex-direction: column; gap: 8px; label { font-size: 14px; display: flex; align-items: flex-start; gap: 8px; cursor: pointer; } }
.ob-checkbox { display: flex; align-items: center; gap: 8px; font-size: 14px; cursor: pointer; }
.ob-form-actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; padding-top: 8px; }
.ob-btn-primary { background: var(--ob-primary); color: #fff; border: none; border-radius: var(--ob-radius); padding: 8px 18px; font-size: 14px; font-weight: 600; cursor: pointer; text-decoration: none; &:hover:not(:disabled) { background: var(--ob-primary-dark); } &:disabled { opacity: 0.6; cursor: not-allowed; } }
.ob-btn-secondary { background: none; border: 1px solid var(--ob-border); border-radius: var(--ob-radius); padding: 8px 18px; font-size: 14px; cursor: pointer; &:hover { background: var(--ob-bg); } }
.ob-btn-danger { background: none; border: 1px solid var(--ob-danger); border-radius: var(--ob-radius); padding: 8px 18px; font-size: 14px; color: var(--ob-danger); cursor: pointer; &:hover { background: #fdf2f2; } }
.ob-error { color: var(--ob-danger); font-size: 13px; }
.ob-success { color: var(--ob-success); font-size: 13px; }
.ob-section { margin-top: 24px; }
.ob-section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; h3 { margin: 0; font-size: 16px; font-weight: 600; } }
.ob-btn-sm-primary { background: var(--ob-primary); color: #fff; border: none; border-radius: 6px; padding: 6px 14px; font-size: 13px; font-weight: 600; text-decoration: none; cursor: pointer; }
.ob-job-row { display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--ob-border); gap: 12px; flex-wrap: wrap; &:last-child { border-bottom: none; } }
.ob-job-name { font-weight: 600; font-size: 14px; }
.ob-cron-code { font-family: monospace; font-size: 12px; color: var(--ob-text-muted); margin-left: 8px; }
.ob-job-actions { display: flex; align-items: center; gap: 8px; }
.ob-btn-sm { background: none; border: 1px solid var(--ob-border); border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer; text-decoration: none; color: var(--ob-text); &:hover { background: var(--ob-bg); } }
.ob-empty { color: var(--ob-text-muted); font-size: 14px; padding: 16px 0; }
</style>
