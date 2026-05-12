"use client";

import useSWR from "swr";
import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { AlertList } from "@/components/AlertList";
import { api } from "@/lib/api";
import type { Alert, AlertStatus } from "@/lib/types";

const FILTERS: Array<{ value: AlertStatus | "all"; label: string }> = [
  { value: "all", label: "All" },
  { value: "open", label: "Open" },
  { value: "acknowledged", label: "Acknowledged" },
  { value: "resolved", label: "Resolved" },
];

export default function AlertsPage() {
  const [filter, setFilter] = useState<AlertStatus | "all">("open");
  const params: Record<string, string> = filter === "all" ? {} : { status: filter };
  const { data, mutate } = useSWR<Alert[]>(
    `/alerts?${filter}`,
    () => api.listAlerts(params) as Promise<Alert[]>,
    { refreshInterval: 15000 }
  );

  return (
    <AppShell title="Alerts">
      <div className="flex items-center gap-2 mb-5">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`px-3 py-1.5 text-sm rounded border ${
              filter === f.value
                ? "border-accent text-accent bg-accent/10"
                : "border-ink-600 text-ink-300 hover:border-ink-500"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <AlertList alerts={data ?? []} onChange={mutate} />
    </AppShell>
  );
}
