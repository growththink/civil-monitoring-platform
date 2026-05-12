"use client";

import { formatDistanceToNow } from "date-fns";
import { AlertCircle, AlertTriangle, CheckCircle2, Info } from "lucide-react";
import { StatusBadge } from "./StatusBadge";
import type { Alert } from "@/lib/types";
import { api } from "@/lib/api";
import { useState } from "react";

const ICONS = {
  info: Info,
  warning: AlertTriangle,
  critical: AlertCircle,
};

const SEVERITY_COLOR = {
  info: "text-accent",
  warning: "text-warn",
  critical: "text-critical",
};

interface Props {
  alerts: Alert[];
  onChange?: () => void;
}

export function AlertList({ alerts, onChange }: Props) {
  const [busy, setBusy] = useState<string | null>(null);

  if (alerts.length === 0) {
    return (
      <div className="text-center py-12 text-ink-400">
        <CheckCircle2 className="w-10 h-10 mx-auto mb-2 text-success" />
        No alerts.
      </div>
    );
  }

  async function ack(id: string) {
    setBusy(id);
    try { await api.acknowledgeAlert(id); onChange?.(); }
    finally { setBusy(null); }
  }

  async function resolve(id: string) {
    setBusy(id);
    try { await api.resolveAlert(id); onChange?.(); }
    finally { setBusy(null); }
  }

  return (
    <div className="space-y-2">
      {alerts.map((alert) => {
        const Icon = ICONS[alert.severity];
        return (
          <div
            key={alert.id}
            className="flex items-start gap-3 p-4 bg-ink-800 border border-ink-700 rounded-lg"
          >
            <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${SEVERITY_COLOR[alert.severity]}`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <span className="font-medium">{alert.title}</span>
                <StatusBadge status={alert.status} size="sm" />
                <StatusBadge status={alert.severity} size="sm" />
              </div>
              <div className="text-sm text-ink-300">{alert.message}</div>
              <div className="text-xs text-ink-400 mt-1">
                {formatDistanceToNow(new Date(alert.ts), { addSuffix: true })}
                {alert.triggered_value !== null && (
                  <span className="ml-3">
                    Value: <span className="font-mono text-ink-200">{alert.triggered_value}</span>
                    {alert.threshold_value !== null && (
                      <span> / Threshold: <span className="font-mono text-ink-200">{alert.threshold_value}</span></span>
                    )}
                  </span>
                )}
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              {alert.status === "open" && (
                <button
                  onClick={() => ack(alert.id)}
                  disabled={busy === alert.id}
                  className="px-3 py-1 text-xs rounded border border-ink-600 hover:border-warn hover:text-warn disabled:opacity-50"
                >
                  Acknowledge
                </button>
              )}
              {alert.status !== "resolved" && (
                <button
                  onClick={() => resolve(alert.id)}
                  disabled={busy === alert.id}
                  className="px-3 py-1 text-xs rounded border border-ink-600 hover:border-success hover:text-success disabled:opacity-50"
                >
                  Resolve
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
