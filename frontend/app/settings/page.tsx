"use client";

import useSWR from "swr";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import type { SystemSetting, User } from "@/lib/types";

const MEASUREMENT_KEY = "measurement_interval_minutes";

export default function SettingsPage() {
  const router = useRouter();
  const { data: me, isLoading: meLoading } = useSWR<User>(
    "/auth/me",
    () => api.me() as Promise<User>,
  );
  const isAdmin = me?.role === "admin" || me?.role === "super_admin";

  const { data: settings, mutate } = useSWR<SystemSetting[]>(
    isAdmin ? "/settings" : null,
    () => api.listSettings() as Promise<SystemSetting[]>,
  );

  const current = settings?.find((s) => s.key === MEASUREMENT_KEY)?.value ?? "60";
  const [interval, setInterval] = useState<string>(current);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setInterval(current);
  }, [current]);

  // Bounce non-admins away
  useEffect(() => {
    if (!meLoading && me && !isAdmin) router.replace("/dashboard");
  }, [meLoading, me, isAdmin, router]);

  async function save(value: string) {
    setSaving(true);
    setError(null);
    try {
      await api.updateSetting(MEASUREMENT_KEY, value);
      await mutate();
      setSavedAt(new Date().toLocaleTimeString());
    } catch (e: any) {
      setError(e?.message ?? "save failed");
      setInterval(current);
    } finally {
      setSaving(false);
    }
  }

  function handleChange(next: string) {
    setInterval(next);
    save(next);
  }

  if (!isAdmin) {
    return (
      <AppShell title="Settings">
        <div className="text-ink-300">Only administrators can view this page.</div>
      </AppShell>
    );
  }

  return (
    <AppShell title="Settings">
      <div className="max-w-2xl space-y-6">
        <section className="bg-ink-800 border border-ink-700 rounded-xl p-6">
          <h2 className="text-base font-semibold mb-1">측정 빈도 (Measurement interval)</h2>
          <p className="text-sm text-ink-400 mb-4">
            Modbus 폴링 주기. 변경 시 스케줄러가 즉시 재예약됩니다.
          </p>

          <div className="space-y-2">
            {[
              { value: "30", label: "30분마다" },
              { value: "60", label: "1시간마다" },
            ].map((opt) => (
              <label
                key={opt.value}
                className="flex items-center gap-3 px-3 py-2 rounded-lg bg-ink-900 border border-ink-700 cursor-pointer hover:border-accent/50"
              >
                <input
                  type="radio"
                  name="interval"
                  value={opt.value}
                  checked={interval === opt.value}
                  onChange={() => handleChange(opt.value)}
                  disabled={saving}
                  className="accent-accent"
                />
                <span className="text-sm">{opt.label}</span>
                <span className="ml-auto text-xs text-ink-500 font-mono">{opt.value} min</span>
              </label>
            ))}
          </div>

          <div className="mt-4 flex items-center gap-3 text-xs">
            {saving && <span className="text-ink-400">저장 중…</span>}
            {!saving && savedAt && (
              <span className="text-emerald-400">저장됨 ({savedAt})</span>
            )}
            {error && <span className="text-red-300">{error}</span>}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
