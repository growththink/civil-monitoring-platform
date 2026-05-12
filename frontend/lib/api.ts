"use client";

import type { TokenPair } from "./types";

const API_BASE = "/api/v1";

const ACCESS_KEY = "civmon_access";
const REFRESH_KEY = "civmon_refresh";

export const tokenStore = {
  get access(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(REFRESH_KEY);
  },
  set(pair: TokenPair) {
    localStorage.setItem(ACCESS_KEY, pair.access_token);
    localStorage.setItem(REFRESH_KEY, pair.refresh_token);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, message: string, body: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function refreshAccessToken(): Promise<boolean> {
  const refresh = tokenStore.refresh;
  if (!refresh) return false;
  const r = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!r.ok) {
    tokenStore.clear();
    return false;
  }
  const pair: TokenPair = await r.json();
  tokenStore.set(pair);
  return true;
}

export async function apiFetch<T = unknown>(
  path: string,
  init: RequestInit = {},
  retry = true
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const headers = new Headers(init.headers || {});
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const access = tokenStore.access;
  if (access) headers.set("Authorization", `Bearer ${access}`);

  const res = await fetch(url, { ...init, headers });

  if (res.status === 401 && retry) {
    const ok = await refreshAccessToken();
    if (ok) return apiFetch<T>(path, init, false);
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new ApiError(401, "Unauthorized", null);
  }

  if (!res.ok) {
    let body: unknown = null;
    try { body = await res.json(); } catch {}
    throw new ApiError(res.status, `${res.status} ${res.statusText}`, body);
  }

  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return (await res.text()) as unknown as T;
}

async function apiUpload<T = unknown>(path: string, form: FormData): Promise<T> {
  // Same auth/refresh path as apiFetch but for multipart/form-data uploads.
  const url = `${API_BASE}${path}`;
  const headers = new Headers();
  const access = tokenStore.access;
  if (access) headers.set("Authorization", `Bearer ${access}`);

  let res = await fetch(url, { method: "POST", headers, body: form });
  if (res.status === 401) {
    const ok = await refreshAccessToken();
    if (!ok) {
      if (typeof window !== "undefined") window.location.href = "/login";
      throw new ApiError(401, "Unauthorized", null);
    }
    const h2 = new Headers();
    const a2 = tokenStore.access;
    if (a2) h2.set("Authorization", `Bearer ${a2}`);
    res = await fetch(url, { method: "POST", headers: h2, body: form });
  }
  if (!res.ok) {
    let body: unknown = null;
    try { body = await res.json(); } catch {}
    throw new ApiError(res.status, `${res.status} ${res.statusText}`, body);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  // Auth
  login: (email: string, password: string) =>
    apiFetch<TokenPair>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }, false),
  me: () => apiFetch("/auth/me"),

  // Sites
  listSites: () => apiFetch("/sites"),
  getSite: (id: string) => apiFetch(`/sites/${id}`),
  listDevicesBySite: (siteId: string) => apiFetch(`/devices?site_id=${siteId}`),
  listSensorsByDevice: (deviceId: string) => apiFetch(`/sensors?device_id=${deviceId}`),

  // Sensors
  getSensor: (id: string) => apiFetch(`/sensors/${id}`),
  updateSensor: (id: string, patch: Record<string, unknown>) =>
    apiFetch(`/sensors/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),

  // Readings
  getReadings: (sensorId: string, window: string) =>
    apiFetch(`/readings/${sensorId}?window=${window}`),

  // Alerts
  listAlerts: (params: Record<string, string> = {}) => {
    const qs = new URLSearchParams(params).toString();
    return apiFetch(`/alerts${qs ? `?${qs}` : ""}`);
  },
  acknowledgeAlert: (id: string, note?: string) =>
    apiFetch(`/alerts/${id}/acknowledge`, {
      method: "POST",
      body: JSON.stringify({ note: note || null }),
    }),
  resolveAlert: (id: string) =>
    apiFetch(`/alerts/${id}/resolve`, { method: "POST" }),

  // Settings
  listSettings: () => apiFetch("/settings"),
  updateSetting: (key: string, value: string) =>
    apiFetch(`/settings/${key}`, {
      method: "PATCH",
      body: JSON.stringify({ value }),
    }),

  // Manual ingest
  uploadManualExcel: (sensorId: string, file: File) => {
    const fd = new FormData();
    fd.append("sensor_id", sensorId);
    fd.append("file", file);
    return apiUpload("/ingest/manual-excel", fd);
  },
};

export { ApiError };
