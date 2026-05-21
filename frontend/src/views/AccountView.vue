<template>
  <div>
    <h2 class="ob-page-title">Account</h2>

    <div class="ob-card ob-form">
      <h3 class="ob-section-title">Change Password</h3>
      <form @submit.prevent="changePassword">
        <div class="ob-field">
          <label>Current Password</label>
          <input v-model="pwForm.current" type="password" required autocomplete="current-password" />
        </div>
        <div class="ob-field">
          <label>New Password</label>
          <input v-model="pwForm.next" type="password" required minlength="8" autocomplete="new-password" />
        </div>
        <div class="ob-field">
          <label>Confirm New Password</label>
          <input v-model="pwForm.confirm" type="password" required autocomplete="new-password" />
        </div>
        <p v-if="pwError" class="ob-error">{{ pwError }}</p>
        <p v-if="pwSuccess" class="ob-success">{{ pwSuccess }}</p>
        <button type="submit" class="ob-btn-primary" :disabled="pwSaving">
          {{ pwSaving ? "Saving…" : "Change Password" }}
        </button>
      </form>
    </div>

    <div class="ob-card" style="margin-top: 20px;">
      <button class="ob-btn-danger" @click="logout">Log out</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { accountApi } from "@/api";

const router = useRouter();
const auth = useAuthStore();

const pwForm = ref({ current: "", next: "", confirm: "" });
const pwError = ref("");
const pwSuccess = ref("");
const pwSaving = ref(false);

async function changePassword(): Promise<void> {
  if (pwForm.value.next !== pwForm.value.confirm) {
    pwError.value = "Passwords do not match.";
    return;
  }
  pwError.value = "";
  pwSaving.value = true;
  try {
    await accountApi.update({}); // refresh user
    // Use the account/change-password endpoint directly via auth change
    const { authApi } = await import("@/api");
    await authApi.changePassword(pwForm.value.current, pwForm.value.next);
    pwSuccess.value = "Password changed successfully.";
    pwForm.value = { current: "", next: "", confirm: "" };
  } catch (e: unknown) {
    pwError.value = e instanceof Error ? e.message : "Failed to change password.";
  } finally {
    pwSaving.value = false;
  }
}

async function logout(): Promise<void> {
  await auth.logout();
  router.push({ name: "login" });
}
</script>

<style scoped lang="scss">
.ob-page-title { font-size: 22px; font-weight: 700; margin: 0 0 20px; }
.ob-section-title { font-size: 15px; font-weight: 600; margin: 0 0 12px; padding-bottom: 8px; border-bottom: 1px solid var(--ob-border); }
.ob-form { display: flex; flex-direction: column; gap: 12px; }
.ob-field { display: flex; flex-direction: column; gap: 4px; label { font-size: 13px; font-weight: 600; } input { padding: 7px 10px; border: 1px solid var(--ob-border); border-radius: 6px; font-size: 14px; outline: none; &:focus { border-color: var(--ob-primary); } } }
.ob-btn-primary { background: var(--ob-primary); color: #fff; border: none; border-radius: var(--ob-radius); padding: 8px 16px; font-size: 14px; font-weight: 600; cursor: pointer; align-self: flex-start; &:hover:not(:disabled) { background: var(--ob-primary-dark); } &:disabled { opacity: 0.6; } }
.ob-btn-danger { background: none; border: 1px solid var(--ob-danger); border-radius: var(--ob-radius); padding: 8px 18px; font-size: 14px; color: var(--ob-danger); cursor: pointer; &:hover { background: #fdf2f2; } }
.ob-success { color: var(--ob-success); font-size: 13px; }
.ob-error { color: var(--ob-danger); font-size: 13px; }
</style>
