"use client";

import useSWR from "swr";
import { AppShell } from "@/components/AppShell";
import { SiteCard } from "@/components/SiteCard";
import { api } from "@/lib/api";
import type { SiteSummary } from "@/lib/types";

export default function SitesPage() {
  const { data } = useSWR<SiteSummary[]>("/sites",
    () => api.listSites() as Promise<SiteSummary[]>,
    { refreshInterval: 30000 }
  );

  return (
    <AppShell title="Sites">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {(data ?? []).map((s) => <SiteCard key={s.id} site={s} />)}
      </div>
    </AppShell>
  );
}
