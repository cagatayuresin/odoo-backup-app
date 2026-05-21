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
      <button class="ob-btn-primary ob-mb" @click="showSmtpForm = !showSmtpForm">
        {{ showSmtpForm ? "Cancel" : "+ Add SMTP Channel" }}
      </button>

      <form v-if="showSmtpForm" class="ob-card ob-form" @submit.prevent="createSmtp">
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
        </div>
        <button type="submit" class="ob-btn-primary">Create</button>
      </form>

      <div v-for="ch in smtpChannels" :key="ch.id" class="ob-card ob-channel-card">
        <div class="ob-channel-info">
          <span class="ob-channel-name">{{ ch.name }}</span>
          <span class="ob-channel-host">{{ ch.host }}:{{ ch.port }}</span>
          <span class="ob-pill" :class="ch.enabled ? 'ob-pill-success' : 'ob-pill-muted'">
            {{ ch.enabled ? "enabled" : "disabled" }}
          </span>
        </div>
        <div class="ob-channel-actions">
          <button class="ob-btn-sm" @click="testSmtp(ch.id)">Send test email</button>
          <button class="ob-btn-sm ob-btn-danger-sm" @click="deleteSmtp(ch.id)">Delete</button>
        </div>
      </div>
    </div>

    <!-- Telegram -->
    <div v-if="activeTab === 'telegram'">
      <button class="ob-btn-primary ob-mb" @click="showTelegramForm = !showTelegramForm">
        {{ showTelegramForm ? "Cancel" : "+ Add Telegram Channel" }}
      </button>

      <form v-if="showTelegramForm" class="ob-card ob-form" @submit.prevent="createTelegram">
        <div class="ob-field"><label>Name</label><input v-model="telegramForm.name" required /></div>
        <div class="ob-field"><label>Bot Token</label><input v-model="telegramForm.bot_token" required /></div>
        <div class="ob-field"><label>Chat ID</label><input v-model="telegramForm.chat_id" required /></div>
        <button type="submit" class="ob-btn-primary">Create</button>
      </form>

      <div v-for="ch in telegramChannels" :key="ch.id" class="ob-card ob-channel-card">
        <div class="ob-channel-info">
          <span class="ob-channel-name">{{ ch.name }}</span>
          <span class="ob-channel-host">Chat: {{ ch.chat_id }}</span>
          <span class="ob-pill" :class="ch.enabled ? 'ob-pill-success' : 'ob-pill-muted'">
            {{ ch.enabled ? "enabled" : "disabled" }}
          </span>
        </div>
        <div class="ob-channel-actions">
          <button class="ob-btn-sm" @click="testTelegram(ch.id)">Send test message</button>
          <button class="ob-btn-sm ob-btn-danger-sm" @click="deleteTelegram(ch.id)">Delete</button>
        </div>
      </div>
    </div>

    <p v-if="msg" class="ob-msg">{{ msg }}</p>
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

const smtpForm = ref({
  name: "", host: "", port: 587, username: "", password: "",
  from_address: "", use_tls: true, use_ssl: false, enabled: true,
});
const telegramForm = ref({ name: "", bot_token: "", chat_id: "", enabled: true });

onMounted(async () => {
  [smtpChannels.value, telegramChannels.value] = await Promise.all([
    channelsApi.listSmtp(),
    channelsApi.listTelegram(),
  ]);
});

async function createSmtp(): Promise<void> {
  await channelsApi.createSmtp(smtpForm.value);
  smtpChannels.value = await channelsApi.listSmtp();
  showSmtpForm.value = false;
}

async function deleteSmtp(id: number): Promise<void> {
  if (!confirm("Delete this SMTP channel?")) return;
  await channelsApi.deleteSmtp(id);
  smtpChannels.value = smtpChannels.value.filter((c) => c.id !== id);
}

async function testSmtp(id: number): Promise<void> {
  try {
    await channelsApi.testSmtp(id);
    msg.value = "Test email sent!";
  } catch (e: unknown) {
    msg.value = e instanceof Error ? e.message : "Test failed";
  }
}

async function createTelegram(): Promise<void> {
  await channelsApi.createTelegram(telegramForm.value);
  telegramChannels.value = await channelsApi.listTelegram();
  showTelegramForm.value = false;
}

async function deleteTelegram(id: number): Promise<void> {
  if (!confirm("Delete this Telegram channel?")) return;
  await channelsApi.deleteTelegram(id);
  telegramChannels.value = telegramChannels.value.filter((c) => c.id !== id);
}

async function testTelegram(id: number): Promise<void> {
  try {
    await channelsApi.testTelegram(id);
    msg.value = "Test message sent!";
  } catch (e: unknown) {
    msg.value = e instanceof Error ? e.message : "Test failed";
  }
}
</script>

<style scoped lang="scss">
.ob-page-title { font-size: 22px; font-weight: 700; margin: 0 0 16px; }
.ob-tabs { display: flex; gap: 4px; margin-bottom: 16px; button { padding: 7px 18px; border: 1px solid var(--ob-border); border-radius: 6px; font-size: 14px; cursor: pointer; background: none; &.active { background: var(--ob-primary); color: #fff; border-color: var(--ob-primary); } } }
.ob-btn-primary { background: var(--ob-primary); color: #fff; border: none; border-radius: var(--ob-radius); padding: 8px 16px; font-size: 14px; font-weight: 600; cursor: pointer; &:hover { background: var(--ob-primary-dark); } }
.ob-mb { margin-bottom: 16px; }
.ob-form { display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px; }
.ob-form-row { display: flex; gap: 12px; flex-wrap: wrap; }
.ob-field { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 160px; &.ob-field-sm { flex: 0 0 90px; min-width: 70px; } label { font-size: 13px; font-weight: 600; } input { padding: 7px 10px; border: 1px solid var(--ob-border); border-radius: 6px; font-size: 14px; outline: none; &:focus { border-color: var(--ob-primary); } } }
.ob-checkbox { display: flex; align-items: center; gap: 6px; font-size: 14px; cursor: pointer; }
.ob-channel-card { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 10px; flex-wrap: wrap; }
.ob-channel-info { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.ob-channel-name { font-weight: 600; font-size: 14px; }
.ob-channel-host { font-size: 12px; color: var(--ob-text-muted); font-family: monospace; }
.ob-channel-actions { display: flex; gap: 8px; }
.ob-btn-sm { background: none; border: 1px solid var(--ob-border); border-radius: 6px; padding: 4px 12px; font-size: 12px; cursor: pointer; &:hover { background: var(--ob-bg); } }
.ob-btn-danger-sm { border-color: var(--ob-danger); color: var(--ob-danger); }
.ob-msg { margin-top: 12px; font-size: 14px; color: var(--ob-success); }
</style>
