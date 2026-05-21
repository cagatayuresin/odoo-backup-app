/**
 * All typed API calls for the odoo-backup-app backend.
 */

import { api } from "./client";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface User {
  id: number;
  username: string;
  must_change_password: boolean;
  timezone: string;
  recovery_email: string | null;
  password_reset_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface Instance {
  id: number;
  name: string;
  slug: string;
  raw_url: string;
  parsed_scheme: string;
  parsed_host: string;
  parsed_port: number;
  backup_method: "odoo_endpoint" | "pg_dump";
  db_host: string | null;
  db_port: number | null;
  db_user: string | null;
  filestore_path: string | null;
  db_selection_mode: "single" | "selected" | "all";
  db_names: string[] | null;
  include_filestore: boolean;
  retention_mode: "keep_last_n" | "older_than_days";
  retention_value: number;
  notifications_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: number;
  instance_id: number;
  name: string;
  cron_expression: string;
  enabled: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BackupRun {
  id: number;
  job_id: number | null;
  instance_id: number;
  started_at: string;
  finished_at: string | null;
  status: "running" | "success" | "failed" | "verified" | "verify_failed";
  file_path: string | null;
  file_size_bytes: number | null;
  db_name: string;
  error_message: string | null;
  verification_status: "not_run" | "passed" | "failed";
  cloud_sync_status: Record<string, string> | null;
}

export interface SmtpChannel {
  id: number;
  name: string;
  host: string;
  port: number;
  username: string;
  from_address: string;
  use_tls: boolean;
  use_ssl: boolean;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface TelegramChannel {
  id: number;
  name: string;
  chat_id: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface CloudAccount {
  id: number;
  provider: "gdrive" | "dropbox" | "onedrive";
  name: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface NotificationBinding {
  id: number;
  instance_id: number;
  channel_type: "smtp" | "telegram";
  channel_id: number;
  on_success: boolean;
  on_failure: boolean;
}

export interface CloudBinding {
  id: number;
  instance_id: number;
  cloud_account_id: number;
  remote_folder: string;
  enabled: boolean;
  apply_retention_remotely: boolean;
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export const authApi = {
  login: (username: string, password: string) =>
    api.post<User>("/auth/login", { username, password }),
  logout: () => api.post<{ detail: string }>("/auth/logout"),
  changePassword: (current_password: string, new_password: string) =>
    api.post<User>("/auth/change-password", { current_password, new_password }),
  requestReset: (username: string) =>
    api.post<{ detail: string }>("/auth/request-reset", { username }),
  resetPassword: (token: string, new_password: string) =>
    api.post<{ detail: string }>("/auth/reset-password", { token, new_password }),
};

// ─── Account ──────────────────────────────────────────────────────────────────

export const accountApi = {
  me: () => api.get<User>("/account/me"),
  update: (data: Partial<User>) => api.patch<User>("/account/me", data),
};

// ─── Instances ────────────────────────────────────────────────────────────────

export const instancesApi = {
  list: () => api.get<Instance[]>("/instances/"),
  get: (id: number) => api.get<Instance>(`/instances/${id}`),
  create: (data: Partial<Instance> & { master_password?: string }) =>
    api.post<Instance>("/instances/", data),
  update: (id: number, data: Partial<Instance> & { master_password?: string }) =>
    api.patch<Instance>(`/instances/${id}`, data),
  delete: (id: number) => api.delete(`/instances/${id}`),
  testConnection: (id: number) =>
    api.post<{ status: string; detail?: string }>(`/instances/${id}/test-connection`),
};

// ─── Jobs ─────────────────────────────────────────────────────────────────────

export const jobsApi = {
  list: (instanceId: number) =>
    api.get<Job[]>(`/instances/${instanceId}/jobs/`),
  get: (instanceId: number, jobId: number) =>
    api.get<Job>(`/instances/${instanceId}/jobs/${jobId}`),
  create: (instanceId: number, data: { name: string; cron_expression: string; enabled: boolean }) =>
    api.post<Job>(`/instances/${instanceId}/jobs/`, data),
  update: (instanceId: number, jobId: number, data: Partial<Job>) =>
    api.patch<Job>(`/instances/${instanceId}/jobs/${jobId}`, data),
  delete: (instanceId: number, jobId: number) =>
    api.delete(`/instances/${instanceId}/jobs/${jobId}`),
  runNow: (instanceId: number, jobId: number) =>
    api.post<{ task_id: string; detail: string }>(`/instances/${instanceId}/jobs/${jobId}/run`),
};

// ─── Backups ──────────────────────────────────────────────────────────────────

export const backupsApi = {
  list: (params?: { instance_id?: number; limit?: number; offset?: number }) =>
    api.get<BackupRun[]>("/backups/", params),
  get: (id: number) => api.get<BackupRun>(`/backups/${id}`),
  delete: (id: number, force?: boolean, confirmation?: string) =>
    api.delete(`/backups/${id}`, { force: force ?? false, confirmation: confirmation ?? "" }),
  verify: (id: number) =>
    api.post<{ task_id: string }>(`/backups/${id}/verify`),
  reupload: (id: number) =>
    api.post<{ task_id: string }>(`/backups/${id}/reupload`),
  downloadUrl: (id: number) => `/api/backups/${id}/download`,
};

// ─── Channels ─────────────────────────────────────────────────────────────────

export const channelsApi = {
  listSmtp: () => api.get<SmtpChannel[]>("/channels/smtp"),
  createSmtp: (data: Omit<SmtpChannel, "id" | "created_at" | "updated_at"> & { password: string }) =>
    api.post<SmtpChannel>("/channels/smtp", data),
  updateSmtp: (id: number, data: Partial<SmtpChannel> & { password?: string }) =>
    api.patch<SmtpChannel>(`/channels/smtp/${id}`, data),
  deleteSmtp: (id: number) => api.delete(`/channels/smtp/${id}`),
  testSmtp: (id: number) =>
    api.post<{ detail: string }>(`/channels/smtp/${id}/test`),

  listTelegram: () => api.get<TelegramChannel[]>("/channels/telegram"),
  createTelegram: (data: { name: string; bot_token: string; chat_id: string; enabled: boolean }) =>
    api.post<TelegramChannel>("/channels/telegram", data),
  updateTelegram: (id: number, data: Partial<TelegramChannel> & { bot_token?: string }) =>
    api.patch<TelegramChannel>(`/channels/telegram/${id}`, data),
  deleteTelegram: (id: number) => api.delete(`/channels/telegram/${id}`),
  testTelegram: (id: number) =>
    api.post<{ detail: string }>(`/channels/telegram/${id}/test`),
};

// ─── Cloud ────────────────────────────────────────────────────────────────────

export const cloudApi = {
  listAccounts: () => api.get<CloudAccount[]>("/cloud/accounts"),
  createAccount: (data: { provider: string; name: string; credentials: Record<string, string>; enabled: boolean }) =>
    api.post<CloudAccount>("/cloud/accounts", data),
  updateAccount: (id: number, data: Partial<CloudAccount> & { credentials?: Record<string, string> }) =>
    api.patch<CloudAccount>(`/cloud/accounts/${id}`, data),
  deleteAccount: (id: number) => api.delete(`/cloud/accounts/${id}`),

  listBindings: (instanceId: number) =>
    api.get<CloudBinding[]>(`/cloud/instances/${instanceId}/bindings`),
  createBinding: (instanceId: number, data: Partial<CloudBinding>) =>
    api.post<CloudBinding>(`/cloud/instances/${instanceId}/bindings`, data),
  updateBinding: (instanceId: number, bindingId: number, data: Partial<CloudBinding>) =>
    api.patch<CloudBinding>(`/cloud/instances/${instanceId}/bindings/${bindingId}`, data),
  deleteBinding: (instanceId: number, bindingId: number) =>
    api.delete(`/cloud/instances/${instanceId}/bindings/${bindingId}`),
};

// ─── Settings ─────────────────────────────────────────────────────────────────

export const settingsApi = {
  timezones: () => api.get<string[]>("/settings/timezones"),
  cronPreview: (expr: string, tz: string, count = 5) =>
    api.get<{ next_runs: string[] }>("/settings/cron/preview", { expr, tz, count }),
};
