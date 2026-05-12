"use client";

import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { AlertTriangle, Cpu, Wifi } from "lucide-react";
import { StatusBadge } from "./StatusBadge";
import type { SiteSummary } from "@/lib/types";

export function SiteCard({ site }: { site: SiteSummary }) {
  const lastSeen = site.last_data_at
    ? formatDistanceToNow(new Date(site.last_data_at), { addSuffix: true })
    : "no data";

  return (
    <Link
      href={`/sites/${site.id}`}
      className="block p-5 bg-ink-800 border border-ink-700 rounded-xl hover:border-accent/50 transition-colors"
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="text-xs text-ink-400 font-mono">{site.code}</div>
          <h3 className="text-lg font-semibold mt-0.5">{site.name}</h3>
        </div>
        <StatusBadge status={site.status} />
      </div>

      <div className="grid grid-cols-3 gap-2 text-sm">
        <div className="flex items-center gap-1.5 text-ink-300">
          <Cpu className="w-4 h-4" />
          <span>{site.sensor_count} sensors</span>
        </div>
        <div className="flex items-center gap-1.5 text-ink-300">
          <Wifi className="w-4 h-4" />
          <span>{site.online_device_count} online</span>
        </div>
        <div className="flex items-center gap-1.5 text-ink-300">
          <AlertTriangle className="w-4 h-4" />
          <span>{site.open_alerts} alerts</span>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-ink-700 text-xs text-ink-400">
        Last data: {lastSeen}
      </div>
    </Link>
  );
}
