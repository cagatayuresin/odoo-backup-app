import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const routes = [
  {
    path: "/login",
    name: "login",
    component: () => import("@/views/LoginView.vue"),
    meta: { public: true },
  },
  {
    path: "/first-login",
    name: "first-login",
    component: () => import("@/views/FirstLoginView.vue"),
    meta: { public: true },
  },
  {
    path: "/reset-password",
    name: "reset-password",
    component: () => import("@/views/ResetPasswordView.vue"),
    meta: { public: true },
  },
  {
    path: "/",
    component: () => import("@/views/AppShell.vue"),
    children: [
      {
        path: "",
        name: "dashboard",
        component: () => import("@/views/DashboardView.vue"),
      },
      {
        path: "instances",
        name: "instances",
        component: () => import("@/views/InstancesView.vue"),
      },
      {
        path: "instances/:id",
        name: "instance-detail",
        component: () => import("@/views/InstanceDetailView.vue"),
        props: true,
      },
      {
        path: "instances/:instanceId/jobs/:jobId?",
        name: "job-editor",
        component: () => import("@/views/JobEditorView.vue"),
        props: true,
      },
      {
        path: "backups",
        name: "backups",
        component: () => import("@/views/BackupsView.vue"),
      },
      {
        path: "channels",
        name: "channels",
        component: () => import("@/views/ChannelsView.vue"),
      },
      {
        path: "cloud",
        name: "cloud",
        component: () => import("@/views/CloudView.vue"),
      },
      {
        path: "settings",
        name: "settings",
        component: () => import("@/views/SettingsView.vue"),
      },
      {
        path: "account",
        name: "account",
        component: () => import("@/views/AccountView.vue"),
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory("/"),
  routes,
});

router.beforeEach(async (to) => {
  if (to.meta.public) return true;

  const auth = useAuthStore();
  if (!auth.user) {
    await auth.fetchMe();
  }

  if (!auth.user) {
    return { name: "login" };
  }

  if (auth.user.must_change_password && to.name !== "first-login") {
    return { name: "first-login" };
  }

  return true;
});

export default router;
