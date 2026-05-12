import clsx from "clsx";

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  normal:       { label: "Normal",       className: "bg-success/15 text-success border-success/40" },
  warning:      { label: "Warning",      className: "bg-warn/15 text-warn border-warn/40" },
  critical:     { label: "Critical",     className: "bg-critical/15 text-critical border-critical/40" },
  disconnected: { label: "Disconnected", className: "bg-ink-300/15 text-ink-300 border-ink-300/40" },
  open:         { label: "Open",         className: "bg-critical/15 text-critical border-critical/40" },
  acknowledged: { label: "Acknowledged", className: "bg-warn/15 text-warn border-warn/40" },
  resolved:     { label: "Resolved",     className: "bg-success/15 text-success border-success/40" },
  info:         { label: "Info",         className: "bg-accent/15 text-accent border-accent/40" },
};

export function StatusBadge({ status, size = "md" }: { status: string; size?: "sm" | "md" }) {
  const cfg = STATUS_CONFIG[status] || {
    label: status,
    className: "bg-ink-700 text-ink-200 border-ink-600",
  };
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border font-medium",
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs",
        cfg.className
      )}
    >
      {cfg.label}
    </span>
  );
}
