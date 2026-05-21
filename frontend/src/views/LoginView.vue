<template>
  <div class="ob-login-page">
    <div class="ob-login-card">
      <div class="ob-login-header">
        <div class="ob-login-logo">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#714B67" stroke-width="2">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
          </svg>
        </div>
        <h1>Odoo Backup Orchestrator</h1>
        <p>Sign in to manage your backups</p>
      </div>

      <form @submit.prevent="handleLogin">
        <div class="ob-field">
          <label>Username</label>
          <input
            v-model="form.username"
            type="text"
            autocomplete="username"
            placeholder="admin"
            required
          />
        </div>
        <div class="ob-field">
          <label>Password</label>
          <input
            v-model="form.password"
            type="password"
            autocomplete="current-password"
            placeholder="••••••••"
            required
          />
        </div>

        <p v-if="error" class="ob-error">{{ error }}</p>

        <button type="submit" class="ob-btn ob-btn-primary" :disabled="loading">
          {{ loading ? "Signing in…" : "Sign in" }}
        </button>

        <p v-if="showForgot" class="ob-forgot">
          <a href="#" @click.prevent="showResetForm = true">Forgot password?</a>
        </p>
      </form>

      <div v-if="showResetForm" class="ob-reset-form">
        <p>Enter your username to receive a reset email.</p>
        <form @submit.prevent="handleReset">
          <div class="ob-field">
            <label>Username</label>
            <input v-model="resetUsername" type="text" required />
          </div>
          <button type="submit" class="ob-btn ob-btn-primary">Send reset email</button>
          <p v-if="resetMsg" class="ob-success">{{ resetMsg }}</p>
        </form>
      </div>
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

const form = ref({ username: "", password: "" });
const error = ref("");
const loading = ref(false);
const showResetForm = ref(false);
const showForgot = ref(true);
const resetUsername = ref("");
const resetMsg = ref("");

async function handleLogin(): Promise<void> {
  error.value = "";
  loading.value = true;
  try {
    const user = await auth.login(form.value.username, form.value.password);
    if (user.must_change_password) {
      router.push({ name: "first-login" });
    } else {
      router.push({ name: "dashboard" });
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "Login failed";
  } finally {
    loading.value = false;
  }
}

async function handleReset(): Promise<void> {
  try {
    await authApi.requestReset(resetUsername.value);
    resetMsg.value = "If recovery is configured, a reset email has been sent.";
  } catch {
    resetMsg.value = "Request sent.";
  }
}
</script>

<style scoped lang="scss">
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

  .ob-login-logo {
    margin-bottom: 12px;
  }

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
    color: var(--ob-text);
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

    &:focus {
      border-color: var(--ob-primary);
    }
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
  transition: background 0.15s;

  &.ob-btn-primary {
    background: var(--ob-primary);
    color: #fff;

    &:hover:not(:disabled) {
      background: var(--ob-primary-dark);
    }

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }
}

.ob-error {
  color: var(--ob-danger);
  font-size: 13px;
  margin-bottom: 12px;
}

.ob-success {
  color: var(--ob-success);
  font-size: 13px;
  margin-top: 8px;
}

.ob-forgot {
  text-align: center;
  margin-top: 12px;
  font-size: 13px;

  a {
    color: var(--ob-accent);
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }
}

.ob-reset-form {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid var(--ob-border);
  font-size: 14px;
}
</style>
