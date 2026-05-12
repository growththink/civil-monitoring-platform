"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Cpu, AlertCircle } from "lucide-react";
import { api, tokenStore } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@civil-monitoring.local");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const tokens = await api.login(email, password);
      tokenStore.set(tokens);
      router.push("/dashboard");
    } catch (err: any) {
      const detail = err?.body?.detail;
      let msg: string;
      if (typeof detail === "string") msg = detail;
      else if (Array.isArray(detail)) msg = detail.map((d: any) => d?.msg ?? JSON.stringify(d)).join("; ");
      else if (detail) msg = JSON.stringify(detail);
      else msg = err?.message || "Login failed";
      setError(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-center gap-2 mb-6">
          <Cpu className="w-8 h-8 text-accent" />
          <div>
            <div className="text-xl font-semibold">Civil Monitoring</div>
            <div className="text-xs text-ink-400">Geotechnical Platform</div>
          </div>
        </div>

        <form
          onSubmit={onSubmit}
          className="bg-ink-800 border border-ink-700 rounded-2xl p-7 space-y-4"
        >
          <div>
            <label className="block text-sm text-ink-300 mb-1.5">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-3 py-2 bg-ink-900 border border-ink-600 rounded-lg text-sm focus:border-accent focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm text-ink-300 mb-1.5">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 bg-ink-900 border border-ink-600 rounded-lg text-sm focus:border-accent focus:outline-none"
            />
          </div>

          {error && (
            <div className="flex items-start gap-2 p-3 bg-critical/10 border border-critical/30 rounded-lg text-sm text-critical">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={busy}
            className="w-full py-2.5 bg-accent hover:bg-accent-dark transition-colors rounded-lg text-sm font-medium disabled:opacity-50"
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
