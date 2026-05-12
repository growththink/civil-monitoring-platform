"use client";

import { ReactNode } from "react";
import { Sidebar } from "./Sidebar";

export function AppShell({ children, title }: { children: ReactNode; title?: string }) {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        {title && (
          <header className="px-8 py-5 border-b border-ink-700 bg-ink-800/50 backdrop-blur sticky top-0 z-10">
            <h1 className="text-xl font-semibold">{title}</h1>
          </header>
        )}
        <div className="p-8">{children}</div>
      </main>
    </div>
  );
}
