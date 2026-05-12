"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import useSWR from "swr";
import { Activity, Bell, Cpu, Home, LogOut, MapPin, Settings, Upload } from "lucide-react";
import clsx from "clsx";
import { api, tokenStore } from "@/lib/api";
import type { User } from "@/lib/types";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: Home, adminOnly: false },
  { href: "/sites", label: "Sites", icon: MapPin, adminOnly: false },
  { href: "/sensors", label: "Sensors", icon: Activity, adminOnly: false },
  { href: "/alerts", label: "Alerts", icon: Bell, adminOnly: false },
  { href: "/manual-upload", label: "Manual Upload", icon: Upload, adminOnly: true },
  { href: "/settings", label: "Settings", icon: Settings, adminOnly: true },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { data: me } = useSWR<User>("/auth/me", () => api.me() as Promise<User>);
  const isAdmin = me?.role === "admin" || me?.role === "super_admin";

  function handleLogout() {
    tokenStore.clear();
    router.push("/login");
  }

  return (
    <aside className="w-60 bg-ink-800 border-r border-ink-700 flex flex-col">
      <div className="p-5 border-b border-ink-700">
        <div className="flex items-center gap-2">
          <Cpu className="w-6 h-6 text-accent" />
          <div>
            <div className="text-sm font-semibold">Civil Monitoring</div>
            <div className="text-xs text-ink-400">Geotech Platform</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {NAV.filter((item) => !item.adminOnly || isAdmin).map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                active
                  ? "bg-accent/15 text-accent"
                  : "text-ink-200 hover:bg-ink-700 hover:text-ink-50"
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          );
        })}
      </nav>

      <button
        onClick={handleLogout}
        className="m-3 flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-ink-300 hover:bg-ink-700 hover:text-ink-50 transition-colors"
      >
        <LogOut className="w-4 h-4" />
        Logout
      </button>
    </aside>
  );
}
