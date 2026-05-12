"use client";

import { use, useEffect, useState } from "react";
import useSWR from "swr";
import { Download } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { SensorChart } from "@/components/SensorChart";
import { StatusBadge } from "@/components/StatusBadge";
import { api, tokenStore } from "@/lib/api";
import { RealtimeClient } from "@/lib/ws";
import type { Device, Sensor, Site, TimeSeriesResponse } from "@/lib/types";

const WINDOWS = [
  { value: "1h", label: "1H" },
  { value: "24h", label: "24H" },
  { value: "7d", label: "7D" },
  { value: "30d", label: "30D" },
];

export default function SiteDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [windowKey, setWindowKey] = useState("24h");

  const { data: site } = useSWR<Site>(`/sites/${id}`, () => api.getSite(id) as Promise<Site>);
  const { data: devices } = useSWR<Device[]>(`/devices?site=${id}`,
    () => api.listDevicesBySite(id) as Promise<Device[]>);

  const [sensors, setSensors] = useState<Sensor[]>([]);
  useEffect(() => {
    if (!devices) return;
    Promise.all(devices.map((d) => api.listSensorsByDevice(d.id) as Promise<Sensor[]>))
      .then((arr) => setSensors(arr.flat()));
  }, [devices]);

  // Live updates
  useEffect(() => {
    const rt = new RealtimeClient(id);
    rt.connect();
    return () => rt.close();
  }, [id]);

  return (
    <AppShell>
      <header className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs text-ink-400 font-mono">{site?.code}</div>
            <h1 className="text-2xl font-semibold mt-1">{site?.name}</h1>
            <div className="text-sm text-ink-400 mt-1">{site?.address}</div>
          </div>
          {site && <StatusBadge status={site.status} />}
        </div>
      </header>

      <div className="flex items-center gap-2 mb-5">
        {WINDOWS.map((w) => (
          <button
            key={w.value}
            onClick={() => setWindowKey(w.value)}
            className={`px-3 py-1.5 text-sm rounded border ${
              windowKey === w.value
                ? "border-accent text-accent bg-accent/10"
                : "border-ink-600 text-ink-300 hover:border-ink-500"
            }`}
          >
            {w.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        {sensors.map((s) => (
          <SensorChartCard key={s.id} sensor={s} windowKey={windowKey} />
        ))}
        {sensors.length === 0 && (
          <div className="col-span-full text-center py-12 text-ink-400">
            No sensors at this site.
          </div>
        )}
      </div>
    </AppShell>
  );
}

function SensorChartCard({ sensor, windowKey }: { sensor: Sensor; windowKey: string }) {
  const { data } = useSWR<TimeSeriesResponse>(
    `/readings/${sensor.id}?w=${windowKey}`,
    () => api.getReadings(sensor.id, windowKey) as Promise<TimeSeriesResponse>,
    { refreshInterval: 30000 }
  );

  function downloadCsv() {
    const now = new Date();
    const from = new Date(now);
    if (windowKey === "1h") from.setHours(from.getHours() - 1);
    else if (windowKey === "24h") from.setDate(from.getDate() - 1);
    else if (windowKey === "7d") from.setDate(from.getDate() - 7);
    else from.setDate(from.getDate() - 30);

    const url =
      `/api/v1/readings/${sensor.id}/export.csv?from_ts=${encodeURIComponent(from.toISOString())}` +
      `&to_ts=${encodeURIComponent(now.toISOString())}`;
    const token = tokenStore.access;
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => r.blob())
      .then((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `${sensor.code}-${windowKey}.csv`;
        a.click();
      });
  }

  return (
    <div className="bg-ink-800 border border-ink-700 rounded-xl p-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="text-xs text-ink-400 font-mono">{sensor.code}</div>
          <div className="text-base font-semibold">{sensor.name}</div>
          <div className="text-xs text-ink-400">
            {sensor.sensor_type} · unit {sensor.unit}
          </div>
        </div>
        <button
          onClick={downloadCsv}
          className="flex items-center gap-1 text-xs text-ink-300 hover:text-accent"
        >
          <Download className="w-4 h-4" />
          CSV
        </button>
      </div>
      <SensorChart sensor={sensor} points={data?.points ?? []} />
    </div>
  );
}
