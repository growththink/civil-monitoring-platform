"use client";

import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import { useRouter } from "next/navigation";
import { Upload } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import type { Device, IngestResult, Sensor, Site, User } from "@/lib/types";

type ManualSensorOption = {
  sensor: Sensor;
  device: Device;
  site: Site;
};

export default function ManualUploadPage() {
  const router = useRouter();
  const { data: me, isLoading: meLoading } = useSWR<User>(
    "/auth/me",
    () => api.me() as Promise<User>,
  );
  const isAdmin = me?.role === "admin" || me?.role === "super_admin";

  const { data: sites } = useSWR<Site[]>(
    isAdmin ? "/sites" : null,
    () => api.listSites() as Promise<Site[]>,
  );
  const [options, setOptions] = useState<ManualSensorOption[]>([]);
  const [sensorId, setSensorId] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<IngestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!meLoading && me && !isAdmin) router.replace("/dashboard");
  }, [meLoading, me, isAdmin, router]);

  useEffect(() => {
    if (!sites) return;
    let cancelled = false;
    (async () => {
      const list: ManualSensorOption[] = [];
      for (const site of sites) {
        const devices = (await api.listDevicesBySite(site.id)) as Device[];
        for (const device of devices) {
          const sensors = (await api.listSensorsByDevice(device.id)) as Sensor[];
          sensors
            .filter((s) => s.ingestion_mode === "manual")
            .forEach((sensor) => list.push({ sensor, device, site }));
        }
      }
      if (!cancelled) setOptions(list);
    })();
    return () => {
      cancelled = true;
    };
  }, [sites]);

  const selected = useMemo(
    () => options.find((o) => o.sensor.id === sensorId),
    [options, sensorId],
  );

  async function handleUpload() {
    if (!sensorId || !file) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const res = (await api.uploadManualExcel(sensorId, file)) as IngestResult;
      setResult(res);
    } catch (e: any) {
      const detail = e?.body?.detail ?? e?.message ?? "upload failed";
      setError(typeof detail === "string" ? detail : JSON.stringify(detail));
    } finally {
      setUploading(false);
    }
  }

  function handleFileChosen(f: File | null) {
    setFile(f);
    setResult(null);
    setError(null);
  }

  if (!isAdmin) {
    return (
      <AppShell title="Manual Upload">
        <div className="text-ink-300">Only administrators can view this page.</div>
      </AppShell>
    );
  }

  return (
    <AppShell title="Manual Upload">
      <div className="max-w-2xl space-y-6">
        <section className="bg-ink-800 border border-ink-700 rounded-xl p-6">
          <h2 className="text-base font-semibold mb-1">엑셀 업로드</h2>
          <p className="text-sm text-ink-400 mb-4">
            컬럼: <span className="font-mono">DATE</span>, <span className="font-mono">TIME</span>,{" "}
            <span className="font-mono">M</span> (측정값)
          </p>

          <div>
            <label className="block text-xs text-ink-400 mb-1.5">센서 선택 (manual 모드만)</label>
            <select
              value={sensorId}
              onChange={(e) => setSensorId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-ink-900 border border-ink-700 text-sm"
            >
              <option value="">— 센서를 선택하세요 —</option>
              {options.map(({ sensor, device, site }) => (
                <option key={sensor.id} value={sensor.id}>
                  {site.code} / {device.code} / {sensor.code} — {sensor.name}
                </option>
              ))}
            </select>
            {options.length === 0 && sites && (
              <p className="text-xs text-ink-500 mt-2">
                Manual 모드로 설정된 센서가 없습니다. Sensors 페이지에서 통신 방식을 Manual 로 변경하세요.
              </p>
            )}
          </div>

          <div
            className={`mt-5 border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
              dragging ? "border-accent bg-accent/5" : "border-ink-700 bg-ink-900/50"
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              const f = e.dataTransfer.files?.[0] ?? null;
              if (f) handleFileChosen(f);
            }}
          >
            <Upload className="w-8 h-8 mx-auto mb-2 text-ink-400" />
            {file ? (
              <div>
                <div className="text-sm font-medium">{file.name}</div>
                <div className="text-xs text-ink-400">{(file.size / 1024).toFixed(1)} KB</div>
                <button
                  type="button"
                  onClick={() => handleFileChosen(null)}
                  className="mt-3 text-xs text-ink-400 underline hover:text-ink-200"
                >
                  파일 제거
                </button>
              </div>
            ) : (
              <>
                <div className="text-sm mb-2">파일을 드래그하거나 선택하세요</div>
                <label className="inline-block cursor-pointer px-4 py-2 rounded-lg bg-ink-700 hover:bg-ink-600 text-sm">
                  파일 선택
                  <input
                    type="file"
                    accept=".xlsx"
                    className="hidden"
                    onChange={(e) => handleFileChosen(e.target.files?.[0] ?? null)}
                  />
                </label>
              </>
            )}
          </div>

          <button
            type="button"
            onClick={handleUpload}
            disabled={!sensorId || !file || uploading}
            className="mt-5 w-full px-4 py-2.5 rounded-lg bg-accent text-ink-900 font-medium hover:bg-accent/90 disabled:opacity-60"
          >
            {uploading ? "업로드 중…" : "업로드"}
          </button>

          {selected && (
            <div className="mt-4 text-xs text-ink-500">
              대상: <span className="font-mono">{selected.sensor.code}</span> ({selected.sensor.name})
            </div>
          )}
        </section>

        {error && (
          <div className="bg-red-500/10 border border-red-500/40 text-red-200 rounded-xl px-4 py-3 text-sm">
            {error}
          </div>
        )}

        {result && (
          <section className="bg-ink-800 border border-ink-700 rounded-xl p-6">
            <h3 className="text-base font-semibold mb-3">결과</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4">
                <div className="text-xs text-emerald-300/80">성공</div>
                <div className="text-2xl font-semibold text-emerald-300">{result.accepted}</div>
              </div>
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                <div className="text-xs text-red-300/80">실패</div>
                <div className="text-2xl font-semibold text-red-300">{result.rejected}</div>
              </div>
            </div>
            {result.errors && result.errors.length > 0 && (
              <details className="mt-4 text-xs">
                <summary className="cursor-pointer text-ink-300">에러 보기 ({result.errors.length})</summary>
                <pre className="mt-2 whitespace-pre-wrap text-red-200 bg-ink-900 p-3 rounded-lg max-h-60 overflow-auto">
                  {result.errors.join("\n")}
                </pre>
              </details>
            )}
          </section>
        )}
      </div>
    </AppShell>
  );
}
