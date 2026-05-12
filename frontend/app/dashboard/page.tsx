"use client";

import useSWR from "swr";
import { useEffect, useState } from "react";
import { Activity, AlertTriangle, MapPin, Wifi, WifiOff } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { SiteCard } from "@/components/SiteCard";
import { AlertList } from "@/components/AlertList";
import { api } from "@/lib/api";
import { RealtimeClient } from "@/lib/ws";
import type { Alert, SiteSummary } from "@/lib/types";

export default function DashboardPage() {
  const { data: sites, mutate: refetchSites } = useSWR<SiteSummary[]>(
    "/sites",
    () => api.listSites() as Promise<SiteSummary[]>,
    { refreshInterval: 30000 }
  );
  const { data: alerts, mutate: refetchAlerts } = useSWR<Alert[]>(
    "/alerts?status=open",
    () => api.listAlerts({ status: "open" }) as Promise<Alert[]>,
    { refreshInterval: 15000 }
  );

  const [liveCount, setLiveCount] = useState(0);

  useEffect(() => {
    const rt = new RealtimeClient();
    rt.connect();
    const off = rt.on((msg) => {
      if (msg.event === "reading") setLiveCount((c) => c + 1);
      if (msg.event === "alert") refetchAlerts();
    });
    return () => { off(); rt.close(); };
  }, [refetchAlerts]);

  const totals = {
    sites: sites?.length ?? 0,
    sensors: sites?.reduce((a, s) => a + s.sensor_count, 0) ?? 0,
    online: sites?.reduce((a, s) => a + s.online_device_count, 0) ?? 0,
    alerts: alerts?.length ?? 0,
  };

  return (
    <AppShell title="Dashboard">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Stat icon={MapPin} label="Sites" value={totals.sites} />
        <Stat icon={Activity} label="Active sensors" value={totals.sensors} />
        <Stat icon={Wifi} label="Online devices" value={totals.online} accent="success" />
        <Stat icon={AlertTriangle} label="Open alerts" value={totals.alerts} accent="critical" />
      </div>

      <section className="mb-10">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">Sites</h2>
          <span className="text-xs text-ink-400">
            Live readings received: {liveCount}
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {(sites ?? []).map((s) => <SiteCard key={s.id} site={s} />)}
          {sites && sites.length === 0 && (
            <div className="col-span-full text-center py-12 text-ink-400">
              No sites yet.
            </div>
          )}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">Open alerts</h2>
        <AlertList alerts={alerts ?? []} onChange={refetchAlerts} />
      </section>
    </AppShell>
  );
}

function Stat({
  icon: Icon, label, value, accent = "accent",
}: {
  icon: any; label: string; value: number; accent?: "accent" | "success" | "critical";
}) {
  const color = {
    accent: "text-accent", success: "text-success", critical: "text-critical",
  }[accent];
  return (
    <div className="bg-ink-800 border border-ink-700 rounded-xl p-5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-ink-300">{label}</span>
        <Icon className={`w-5 h-5 ${color}`} />
      </div>
      <div className="text-2xl font-semibold">{value}</div>
    </div>
  );
}
