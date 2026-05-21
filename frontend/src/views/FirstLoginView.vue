<template>
  <div class="ob-login-page">
    <div class="ob-login-card">
      <div class="ob-login-header">
        <h1>Change Your Password</h1>
        <p>You must set a new password before continuing.</p>
      </div>

      <form @submit.prevent="handleChange">
        <div class="ob-field">
          <label>Current Password</label>
          <input v-model="form.current" type="password" required autocomplete="current-password" />
        </div>
        <div class="ob-field">
          <label>New Password</label>
          <input
            v-model="form.next"
            type="password"
            required
            autocomplete="new-password"
            minlength="8"
          />
        </div>
        <div class="ob-field">
          <label>Confirm New Password</label>
          <input v-model="form.confirm" type="password" required autocomplete="new-password" />
        </div>

        <p v-if="error" class="ob-error">{{ error }}</p>

        <button type="submit" class="ob-btn ob-btn-primary" :disabled="loading">
          {{ loading ? "Saving…" : "Set Password &amp; Continue" }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { authApi } from "@/api";

const router = useRouter();
const auth = useAuthStore();
const form = ref({ current: "", next: "", confirm: "" });
const error = ref("");
const loading = ref(false);

async function handleChange(): Promise<void> {
  if (form.value.next !== form.value.confirm) {
    error.value = "Passwords do not match.";
    return;
  }
  if (form.value.next.length < 8) {
    error.value = "Password must be at least 8 characters.";
    return;
  }

  error.value = "";
  loading.value = true;
  try {
    const user = await authApi.changePassword(form.value.current, form.value.next);
    auth.user = user;
    router.push({ name: "dashboard" });
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "Failed to change password.";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped lang="scss">
@import "@/assets/theme.scss";

.ob-login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ob-bg);
  padding: 16px;
}

.ob-login-card {
  background: var(--ob-surface);
  border: 1px solid var(--ob-border);
  border-radius: var(--ob-radius);
  box-shadow: var(--ob-shadow);
  padding: 40px;
  width: 100%;
  max-width: 400px;
}

.ob-login-header {
  text-align: center;
  margin-bottom: 32px;

  h1 {
    font-size: 20px;
    font-weight: 700;
    color: var(--ob-primary);
    margin: 0 0 4px;
  }

  p {
    color: var(--ob-text-muted);
    font-size: 14px;
    margin: 0;
  }
}

.ob-field {
  margin-bottom: 16px;

  label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 6px;
  }

  input {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid var(--ob-border);
    border-radius: var(--ob-radius);
    font-size: 14px;
    outline: none;
    transition: border-color 0.15s;

    &:focus { border-color: var(--ob-primary); }
  }
}

.ob-btn {
  width: 100%;
  padding: 10px;
  border: none;
  border-radius: var(--ob-radius);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;

  &.ob-btn-primary {
    background: var(--ob-primary);
    color: #fff;

    &:hover:not(:disabled) { background: var(--ob-primary-dark); }
    &:disabled { opacity: 0.6; cursor: not-allowed; }
  }
}

.ob-error { color: var(--ob-danger); font-size: 13px; margin-bottom: 12px; }
</style>
