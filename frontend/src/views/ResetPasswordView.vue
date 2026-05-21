<template>
  <div class="ob-login-page">
    <div class="ob-login-card">
      <div class="ob-login-header">
        <h1>Reset Your Password</h1>
      </div>

      <form @submit.prevent="handleReset">
        <div class="ob-field">
          <label>New Password</label>
          <input v-model="form.password" type="password" required minlength="8" />
        </div>
        <div class="ob-field">
          <label>Confirm Password</label>
          <input v-model="form.confirm" type="password" required />
        </div>
        <p v-if="error" class="ob-error">{{ error }}</p>
        <p v-if="success" class="ob-success">{{ success }}</p>
        <button type="submit" class="ob-btn ob-btn-primary" :disabled="loading">
          {{ loading ? "Saving…" : "Reset Password" }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { authApi } from "@/api";

const route = useRoute();
const router = useRouter();
const token = ref("");
const form = ref({ password: "", confirm: "" });
const error = ref("");
const success = ref("");
const loading = ref(false);

onMounted(() => {
  token.value = (route.query.token as string) ?? "";
  if (!token.value) error.value = "No reset token provided.";
});

async function handleReset(): Promise<void> {
  if (form.value.password !== form.value.confirm) {
    error.value = "Passwords do not match.";
    return;
  }
  error.value = "";
  loading.value = true;
  try {
    await authApi.resetPassword(token.value, form.value.password);
    success.value = "Password reset! Redirecting to login…";
    setTimeout(() => router.push({ name: "login" }), 2000);
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "Reset failed.";
  } finally {
    loading.value = false;
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
  padding: 40px;
  width: 100%;
  max-width: 400px;
}
.ob-login-header { text-align: center; margin-bottom: 24px; h1 { font-size: 20px; font-weight: 700; color: var(--ob-primary); margin: 0; } }
.ob-field { margin-bottom: 16px; label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; } input { width: 100%; padding: 8px 12px; border: 1px solid var(--ob-border); border-radius: var(--ob-radius); font-size: 14px; outline: none; &:focus { border-color: var(--ob-primary); } } }
.ob-btn { width: 100%; padding: 10px; border: none; border-radius: var(--ob-radius); font-size: 14px; font-weight: 600; cursor: pointer; &.ob-btn-primary { background: var(--ob-primary); color: #fff; &:hover:not(:disabled) { background: var(--ob-primary-dark); } &:disabled { opacity: 0.6; cursor: not-allowed; } } }
.ob-error { color: var(--ob-danger); font-size: 13px; margin-bottom: 12px; }
.ob-success { color: var(--ob-success); font-size: 13px; margin-bottom: 12px; }
</style>
