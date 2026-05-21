<template>
  <div>
    <h2 class="ob-page-title">Notification Channels</h2>

    <!-- SMTP Tab / Telegram Tab -->
    <div class="ob-tabs">
      <button :class="{ active: activeTab === 'smtp' }" @click="activeTab = 'smtp'">SMTP Email</button>
      <button :class="{ active: activeTab === 'telegram' }" @click="activeTab = 'telegram'">Telegram</button>
    </div>

    <!-- SMTP -->
    <div v-if="activeTab === 'smtp'">
      <button class="ob-btn-primary ob-mb" @click="showSmtpForm = !showSmtpForm; editingSmtpId = null">
        {{ showSmtpForm && editingSmtpId === null ? "Cancel" : "+ Add SMTP Channel" }}
      </button>

      <form v-if="showSmtpForm && editingSmtpId === null" class="ob-card ob-form" @submit.prevent="createSmtp">
        <div class="ob-form-row">
          <div class="ob-field"><label>Name</label><input v-model="smtpForm.name" required /></div>
          <div class="ob-field"><label>Host</label><input v-model="smtpForm.host" required /></div>
          <div class="ob-field ob-field-sm"><label>Port</label><input v-model.number="smtpForm.port" type="number" /></div>
        </div>
        <div class="ob-form-row">
          <div class="ob-field"><label>Username</label><input v-model="smtpForm.username" required /></div>
          <div class="ob-field"><label>Password</label><input v-model="smtpForm.password" type="password" required /></div>
        </div>
        <div class="ob-field"><label>From Address</label><input v-model="smtpForm.from_address" required /></div>
        <div class="ob-form-row">
          <label class="ob-checkbox"><input v-model="smtpForm.use_tls" type="checkbox" /> STARTTLS</label>
          <label class="ob-checkbox"><input v-model="smtpForm.use_ssl" type="checkbox" /> SSL/TLS</label>
          <label class="ob-checkbox"><input v-model="smtpForm.enabled" type="checkbox" /> Enabled</label>
        </div>
        <button type="submit" class="ob-btn-primary">Create</button>
      </form>

      <div v-for="ch in smtpChannels" :key="ch.id" class="ob-card ob-channel-card-wrap">
        <div class="ob-channel-card">
          <div class="ob-channel-info">
            <span class="ob-channel-name">{{ ch.name }}</span>
            <span class="ob-channel-host">{{ ch.host }}:{{ ch.port }}</span>
            <span class="ob-pill" :class="ch.enabled ? 'ob-pill-success' : 'ob-pill-muted'">
              {{ ch.enabled ? "enabled" : "disabled" }}
            </span>
          </div>
          <div class="ob-channel-actions">
            <button class="ob-btn-sm" @click="testSmtp(ch.id)">Send test email</button>
            <button class="ob-btn-sm" @click="startEditSmtp(ch)">Edit</button>
            <button class="ob-btn-sm ob-btn-danger-sm" @click="deleteSmtp(ch.id)">Delete</button>
          </div>
        </div>

        <form v-if="editingSmtpId === ch.id" class="ob-edit-form" @submit.prevent="saveSmtp(ch.id)">
          <div class="ob-form-row">
            <div class="ob-field"><label>Name</label><input v-model="smtpEditForm.name" required /></div>
            <div class="ob-field"><label>Host</label><input v-model="smtpEditForm.host" required /></div>
            <div class="ob-field ob-field-sm"><label>Port</label><input v-model.number="smtpEditForm.port" type="number" /></div>
          </div>
          <div class="ob-form-row">
            <div class="ob-field"><label>Username</label><input v-model="smtpEditForm.username" required /></div>
            <div class="ob-field"><label>New Password <span class="ob-hint-inline">(leave blank to keep)</span></label><input v-model="smtpEditForm.password" type="password" /></div>
          </div>
          <div class="ob-field"><label>From Address</label><input v-model="smtpEditForm.from_address" required /></div>
          <div class="ob-form-row">
            <label class="ob-checkbox"><input v-model="smtpEditForm.use_tls" type="checkbox" /> STARTTLS</label>
            <label class="ob-checkbox"><input v-model="smtpEditForm.use_ssl" type="checkbox" /> SSL/TLS</label>
            <label class="ob-checkbox"><input v-model="smtpEditForm.enabled" type="checkbox" /> Enabled</label>
          </div>
          <div class="ob-form-row">
            <button type="submit" class="ob-btn-primary">Save</button>
            <button type="button" class="ob-btn-sm" @click="editingSmtpId = null">Cancel</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Telegram -->
    <div v-if="activeTab === 'telegram'">
      <button class="ob-btn-primary ob-mb" @click="showTelegramForm = !showTelegramForm; editingTelegramId = null">
        {{ showTelegramForm && editingTelegramId === null ? "Cancel" : "+ Add Telegram Channel" }}
      </button>

      <form v-if="showTelegramForm && editingTelegramId === null" class="ob-card ob-form" @submit.prevent="createTelegram">
        <div class="ob-field"><label>Name</label><input v-model="telegramForm.name" required /></div>
        <div class="ob-field"><label>Bot Token</label><input v-model="telegramForm.bot_token" required /></div>
        <div class="ob-field"><label>Chat ID</label><input v-model="telegramForm.chat_id" required /></div>
        <button type="submit" class="ob-btn-primary">Create</button>
      </form>

      <div v-for="ch in telegramChannels" :key="ch.id" class="ob-card ob-channel-card-wrap">
        <div class="ob-channel-card">
          <div class="ob-channel-info">
            <span class="ob-channel-name">{{ ch.name }}</span>
            <span class="ob-channel-host">Chat: {{ ch.chat_id }}</span>
            <span class="ob-pill" :class="ch.enabled ? 'ob-pill-success' : 'ob-pill-muted'">
              {{ ch.enabled ? "enabled" : "disabled" }}
            </span>
          </div>
          <div class="ob-channel-actions">
            <button class="ob-btn-sm" @click="testTelegram(ch.id)">Send test message</button>
            <button class="ob-btn-sm" @click="startEditTelegram(ch)">Edit</button>
            <button class="ob-btn-sm ob-btn-danger-sm" @click="deleteTelegram(ch.id)">Delete</button>
          </div>
        </div>

        <form v-if="editingTelegramId === ch.id" class="ob-edit-form" @submit.prevent="saveTelegram(ch.id)">
          <div class="ob-field"><label>Name</label><input v-model="telegramEditForm.name" required /></div>
          <div class="ob-field"><label>New Bot Token <span class="ob-hint-inline">(leave blank to keep)</span></label><input v-model="telegramEditForm.bot_token" /></div>
          <div class="ob-field"><label>Chat ID</label><input v-model="telegramEditForm.chat_id" required /></div>
          <label class="ob-checkbox" style="margin-bottom: 8px;"><input v-model="telegramEditForm.enabled" type="checkbox" /> Enabled</label>
          <div class="ob-form-row">
            <button type="submit" class="ob-btn-primary">Save</button>
            <button type="button" class="ob-btn-sm" @click="editingTelegramId = null">Cancel</button>
          </div>
        </form>
      </div>
    </div>

    <p v-if="msg" :class="msgOk ? 'ob-msg-ok' : 'ob-msg-err'">{{ msg }}</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import type { SmtpChannel, TelegramChannel } from "@/api";
import { channelsApi } from "@/api";

const activeTab = ref("smtp");
const smtpChannels = ref<SmtpChannel[]>([]);
const telegramChannels = ref<TelegramChannel[]>([]);
const showSmtpForm = ref(false);
const showTelegramForm = ref(false);
const msg = ref("");
const msgOk = ref(true);

const editingSmtpId = ref<number | null>(null);
const editingTelegramId = ref<number | null>(null);

const smtpForm = ref({
  name: "", host: "", port: 587, username: "", password: "",
  from_address: "", use_tls: true, use_ssl: false, enabled: true,
});
const smtpEditForm = ref({
  name: "", host: "", port: 587, username: "", password: "",
  from_address: "", use_tls: true, use_ssl: false, enabled: true,
});
const telegramForm = ref({ name: "", bot_token: "", chat_id: "", enabled: true });
const telegramEditForm = ref({ name: "", bot_token: "", chat_id: "", enabled: true });

onMounted(async () => {
  [smtpChannels.value, telegramChannels.value] = await Promise.all([
    channelsApi.listSmtp(),
    channelsApi.listTelegram(),
  ]);
});

function setMsg(text: string, ok = true): void {
  msg.value = text;
  msgOk.value = ok;
}

async function createSmtp(): Promise<void> {
  try {
    await channelsApi.createSmtp(smtpForm.value);
    smtpChannels.value = await channelsApi.listSmtp();
    showSmtpForm.value = false;
    setMsg("SMTP channel created.");
  } catch (e: unknown) {
    setMsg(e instanceof Error ? e.message : "Create failed.", false);
  }
}

function startEditSmtp(ch: SmtpChannel): void {
  editingSmtpId.value = editingSmtpId.value === ch.id ? null : ch.id;
  showSmtpForm.value = false;
  smtpEditForm.value = {
    name: ch.name, host: ch.host, port: ch.port, username: ch.username,
    password: "", from_address: ch.from_address, use_tls: ch.use_tls,
    use_ssl: ch.use_ssl, enabled: ch.enabled,
  };
}

async function saveSmtp(id: number): Promise<void> {
  try {
    const payload: Record<string, unknown> = { ...smtpEditForm.value };
    if (!payload.password) delete payload.password;
    await channelsApi.updateSmtp(id, payload as Parameters<typeof channelsApi.updateSmtp>[1]);
    smtpChannels.value = await channelsApi.listSmtp();
    editingSmtpId.value = null;
    setMsg("SMTP channel updated.");
  } catch (e: unknown) {
    setMsg(e instanceof Error ? e.message : "Update failed.", false);
  }
}

async function deleteSmtp(id: number): Promise<void> {
  if (!confirm("Delete this SMTP channel?")) return;
  try {
    await channelsApi.deleteSmtp(id);
    smtpChannels.value = smtpChannels.value.filter((c) => c.id !== id);
    if (editingSmtpId.value === id) editingSmtpId.value = null;
    setMsg("SMTP channel deleted.");
  } catch (e: unknown) {
    setMsg(e instanceof Error ? e.message : "Delete failed.", false);
  }
}

async function testSmtp(id: number): Promise<void> {
  try {
    await channelsApi.testSmtp(id);
    setMsg("Test email sent! Check your inbox.");
  } catch (e: unknown) {
    setMsg(e instanceof Error ? e.message : "Test failed.", false);
  }
}

async function createTelegram(): Promise<void> {
  try {
    await channelsApi.createTelegram(telegramForm.value);
    telegramChannels.value = await channelsApi.listTelegram();
    showTelegramForm.value = false;
    setMsg("Telegram channel created.");
  } catch (e: unknown) {
    setMsg(e instanceof Error ? e.message : "Create failed.", false);
  }
}

function startEditTelegram(ch: TelegramChannel): void {
  editingTelegramId.value = editingTelegramId.value === ch.id ? null : ch.id;
  showTelegramForm.value = false;
  telegramEditForm.value = { name: ch.name, bot_token: "", chat_id: ch.chat_id, enabled: ch.enabled };
}

async function saveTelegram(id: number): Promise<void> {
  try {
    const payload: Record<string, unknown> = { ...telegramEditForm.value };
    if (!payload.bot_token) delete payload.bot_token;
    await channelsApi.updateTelegram(id, payload as Parameters<typeof channelsApi.updateTelegram>[1]);
    telegramChannels.value = await channelsApi.listTelegram();
    editingTelegramId.value = null;
    setMsg("Telegram channel updated.");
  } catch (e: unknown) {
    setMsg(e instanceof Error ? e.message : "Update failed.", false);
  }
}

async function deleteTelegram(id: number): Promise<void> {
  if (!confirm("Delete this Telegram channel?")) return;
  try {
    await channelsApi.deleteTelegram(id);
    telegramChannels.value = telegramChannels.value.filter((c) => c.id !== id);
    if (editingTelegramId.value === id) editingTelegramId.value = null;
    setMsg("Telegram channel deleted.");
  } catch (e: unknown) {
    setMsg(e instanceof Error ? e.message : "Delete failed.", false);
  }
}

async function testTelegram(id: number): Promise<void> {
  try {
    await channelsApi.testTelegram(id);
    setMsg("Test message sent!");
  } catch (e: unknown) {
    setMsg(e instanceof Error ? e.message : "Test failed.", false);
  }
}
</script>

<style scoped lang="scss">
.ob-page-title { font-size: 22px; font-weight: 700; margin: 0 0 16px; }
.ob-tabs { display: flex; gap: 4px; margin-bottom: 16px; button { padding: 7px 18px; border: 1px solid var(--ob-border); border-radius: 6px; font-size: 14px; cursor: pointer; background: none; &.active { background: var(--ob-primary); color: #fff; border-color: var(--ob-primary); } } }
.ob-btn-primary { background: var(--ob-primary); color: #fff; border: none; border-radius: var(--ob-radius); padding: 8px 16px; font-size: 14px; font-weight: 600; cursor: pointer; &:hover { background: var(--ob-primary-dark); } }
.ob-mb { margin-bottom: 16px; display: block; }
.ob-form { display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px; }
.ob-edit-form { display: flex; flex-direction: column; gap: 12px; padding-top: 16px; border-top: 1px solid var(--ob-border); margin-top: 12px; }
.ob-form-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-end; }
.ob-field { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 160px; &.ob-field-sm { flex: 0 0 90px; min-width: 70px; } label { font-size: 13px; font-weight: 600; } input { padding: 7px 10px; border: 1px solid var(--ob-border); border-radius: 6px; font-size: 14px; outline: none; &:focus { border-color: var(--ob-primary); } } }
.ob-hint-inline { font-size: 11px; color: var(--ob-text-muted); font-weight: 400; }
.ob-checkbox { display: flex; align-items: center; gap: 6px; font-size: 14px; cursor: pointer; }
.ob-channel-card-wrap { margin-bottom: 10px; }
.ob-channel-card { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.ob-channel-info { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.ob-channel-name { font-weight: 600; font-size: 14px; }
.ob-channel-host { font-size: 12px; color: var(--ob-text-muted); font-family: monospace; }
.ob-channel-actions { display: flex; gap: 8px; }
.ob-btn-sm { background: none; border: 1px solid var(--ob-border); border-radius: 6px; padding: 4px 12px; font-size: 12px; cursor: pointer; &:hover { background: var(--ob-bg); } }
.ob-btn-danger-sm { border-color: var(--ob-danger); color: var(--ob-danger); }
.ob-msg-ok { margin-top: 12px; font-size: 14px; color: var(--ob-success); display: block; }
.ob-msg-err { margin-top: 12px; font-size: 14px; color: var(--ob-danger); display: block; }
</style>
