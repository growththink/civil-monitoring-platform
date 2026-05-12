"use client";

import useSWR from "swr";
import Link from "next/link";
import { useEffect, useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import type { Device, IngestionMode, Sensor, Site, User } from "@/lib/types";

type Row = { site: Site; sensor: Sensor; device: Device };

export default function SensorsPage() {
  const { data: sites } = useSWR<Site[]>("/sites", () => api.listSites() as Promise<Site[]>);
  const { data: me } = useSWR<User>("/auth/me", () => api.me() as Promise<User>);
  const isAdmin = me?.role === "admin" || me?.role === "super_admin";

  const [rows, setRows] = useState<Row[]>([]);
  const [editing, setEditing] = useState<Row | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    if (!sites) return;
    let cancelled = false;
    (async () => {
      const result: Row[] = [];
      for (const site of sites) {
        const devices = (await api.listDevicesBySite(site.id)) as Device[];
        for (const device of devices) {
          const sensors = (await api.listSensorsByDevice(device.id)) as Sensor[];
          sensors.forEach((sensor) => result.push({ site, sensor, device }));
        }
      }
      if (!cancelled) setRows(result);
    })();
    return () => {
      cancelled = true;
    };
  }, [sites, reloadTick]);

  return (
    <AppShell title="Sensors">
      <div className="overflow-x-auto bg-ink-800 border border-ink-700 rounded-xl">
        <table className="w-full text-sm">
          <thead className="text-xs text-ink-400 border-b border-ink-700">
            <tr>
              <th className="px-4 py-3 text-left">Sensor</th>
              <th className="px-4 py-3 text-left">Type</th>
              <th className="px-4 py-3 text-left">Unit</th>
              <th className="px-4 py-3 text-left">Ingestion</th>
              <th className="px-4 py-3 text-left">Site</th>
              <th className="px-4 py-3 text-left">Device</th>
              <th className="px-4 py-3 text-left">Last reading</th>
              {isAdmin && <th className="px-4 py-3 text-right">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const { sensor, device, site } = row;
              return (
                <tr key={sensor.id} className="border-b border-ink-700/50 hover:bg-ink-700/30">
                  <td className="px-4 py-3">
                    <div className="font-medium">{sensor.name}</div>
                    <div className="text-xs text-ink-400 font-mono">{sensor.code}</div>
                  </td>
                  <td className="px-4 py-3 text-ink-300">{sensor.sensor_type}</td>
                  <td className="px-4 py-3 font-mono text-ink-200">{sensor.unit}</td>
                  <td className="px-4 py-3">
                    <IngestionPill mode={sensor.ingestion_mode} />
                  </td>
                  <td className="px-4 py-3">
                    <Link href={`/sites/${site.id}`} className="text-accent hover:underline">
                      {site.code}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-ink-300">{device.code}</td>
                  <td className="px-4 py-3 text-ink-300">
                    {sensor.last_reading_at
                      ? formatDistanceToNow(new Date(sensor.last_reading_at), { addSuffix: true })
                      : "—"}
                  </td>
                  {isAdmin && (
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => setEditing(row)}
                        className="px-3 py-1.5 rounded-lg text-xs bg-accent/15 text-accent hover:bg-accent/25"
                      >
                        Edit
                      </button>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {editing && (
        <SensorEditModal
          row={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            setReloadTick((t) => t + 1);
          }}
        />
      )}
    </AppShell>
  );
}

function IngestionPill({ mode }: { mode: IngestionMode }) {
  const cls = {
    modbus: "bg-orange-500/15 text-orange-300",
    mqtt: "bg-emerald-500/15 text-emerald-300",
    manual: "bg-sky-500/15 text-sky-300",
  }[mode] ?? "bg-ink-700 text-ink-300";
  return <span className={`px-2 py-0.5 rounded-full text-xs font-mono ${cls}`}>{mode}</span>;
}

function SensorEditModal({
  row,
  onClose,
  onSaved,
}: {
  row: Row;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { sensor, site } = row;
  const [mode, setMode] = useState<IngestionMode>(sensor.ingestion_mode);
  const [registerAddr, setRegisterAddr] = useState(
    sensor.modbus_register_address?.toString() ?? ""
  );
  const [registerCount, setRegisterCount] = useState(
    (sensor.modbus_register_count ?? 2).toString()
  );
  const [dataType, setDataType] = useState(sensor.modbus_data_type ?? "float32");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const patch: Record<string, unknown> = { ingestion_mode: mode };
      if (mode === "modbus") {
        const addr = registerAddr.trim() === "" ? null : parseInt(registerAddr, 10);
        const count = registerCount.trim() === "" ? 2 : parseInt(registerCount, 10);
        if (addr !== null && Number.isNaN(addr)) throw new Error("register address must be a number");
        if (Number.isNaN(count)) throw new Error("register count must be a number");
        patch.modbus_register_address = addr;
        patch.modbus_register_count = count;
        patch.modbus_data_type = dataType;
      }
      await api.updateSensor(sensor.id, patch);
      onSaved();
    } catch (e: any) {
      setError(e?.message ?? "save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-30 bg-black/60 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg bg-ink-800 border border-ink-700 rounded-xl p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold mb-1">Edit sensor</h2>
        <p className="text-sm text-ink-400 mb-5">
          {sensor.code} · {sensor.name}
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-xs text-ink-400 mb-1.5">통신 방식 (Ingestion mode)</label>
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as IngestionMode)}
              className="w-full px-3 py-2 rounded-lg bg-ink-900 border border-ink-700 text-sm"
            >
              <option value="modbus">Modbus</option>
              <option value="mqtt">MQTT</option>
              <option value="manual">Manual (Excel upload)</option>
            </select>
          </div>

          {mode === "modbus" && (
            <div className="space-y-3 pl-3 border-l-2 border-orange-500/40">
              <div>
                <label className="block text-xs text-ink-400 mb-1.5">Register address</label>
                <input
                  type="number"
                  value={registerAddr}
                  onChange={(e) => setRegisterAddr(e.target.value)}
                  placeholder="e.g. 40001"
                  className="w-full px-3 py-2 rounded-lg bg-ink-900 border border-ink-700 text-sm font-mono"
                />
              </div>
              <div>
                <label className="block text-xs text-ink-400 mb-1.5">Register count</label>
                <input
                  type="number"
                  value={registerCount}
                  onChange={(e) => setRegisterCount(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-ink-900 border border-ink-700 text-sm font-mono"
                />
              </div>
              <div>
                <label className="block text-xs text-ink-400 mb-1.5">Data type</label>
                <select
                  value={dataType}
                  onChange={(e) => setDataType(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-ink-900 border border-ink-700 text-sm"
                >
                  <option value="float32">float32</option>
                  <option value="int32">int32</option>
                  <option value="uint32">uint32</option>
                  <option value="int16">int16</option>
                  <option value="uint16">uint16</option>
                </select>
              </div>
            </div>
          )}

          {mode === "mqtt" && (
            <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/30 text-sm text-emerald-200">
              MQTT 토픽:
              <div className="mt-1 font-mono text-xs">
                sites/{site.code}/sensors/{sensor.code}/data
              </div>
              <div className="mt-1 text-xs text-emerald-200/70">
                위 토픽으로 JSON payload를 보내주세요. (device_code, sensor_code, ts, value, quality)
              </div>
            </div>
          )}

          {mode === "manual" && (
            <div className="p-3 rounded-lg bg-sky-500/5 border border-sky-500/30 text-sm text-sky-200">
              수동 업로드 모드입니다. 사이드바의 <b>Manual Upload</b> 페이지에서 엑셀
              파일(DATE / TIME / M 컬럼)을 올려주세요.
            </div>
          )}

          {error && (
            <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
              {error}
            </div>
          )}
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm bg-ink-700 hover:bg-ink-600"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={saving}
            onClick={handleSave}
            className="px-4 py-2 rounded-lg text-sm bg-accent text-ink-900 font-medium hover:bg-accent/90 disabled:opacity-60"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
