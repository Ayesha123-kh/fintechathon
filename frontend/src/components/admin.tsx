"use client";

import clsx from "clsx";
import { Search } from "lucide-react";
import { Card, Input } from "./ui";

/** Title block at the top of every admin page. */
export function PageHeader({ title, subtitle, children }: { title: string; subtitle?: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold tracking-tight md:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

/** A small number tile. */
export function Stat({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <Card className="p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className="tabular mt-1 text-2xl font-bold">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
    </Card>
  );
}

const TONES = {
  neutral: "bg-surface-2 text-ink-2 ring-1 ring-line",
  good: "bg-forest text-forest-ink",
  soft: "bg-primary/40 text-ink",
  bad: "bg-danger/10 text-danger",
} as const;

export function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: keyof typeof TONES }) {
  return <span className={clsx("inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap", TONES[tone])}>{children}</span>;
}

/** A row of toggle chips; `value` is the selected id. */
export function Chips<T extends string>({ options, value, onChange, label }: {
  options: { id: T; label: string; count?: number }[]; value: T; onChange: (id: T) => void; label: string;
}) {
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.id} type="button" aria-pressed={value === o.id} onClick={() => onChange(o.id)}
          className={clsx("rounded-full px-3 py-1.5 text-xs font-semibold", value === o.id ? "bg-forest text-forest-ink" : "bg-surface-2 text-ink-2 ring-1 ring-line hover:bg-hover")}>
          {o.label}{o.count !== undefined && <span className="ml-1 opacity-70">{o.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function SearchBox({ value, onChange, placeholder, label }: {
  value: string; onChange: (v: string) => void; placeholder: string; label: string;
}) {
  return (
    <div className="relative min-w-48 flex-1">
      <Search className="pointer-events-none absolute top-1/2 left-4 z-10 size-4 -translate-y-1/2 text-muted" aria-hidden />
      <Input placeholder={placeholder} value={value} onChange={(e) => onChange(e.target.value)} className="h-10 pl-10" aria-label={label} />
    </div>
  );
}

/** Scrolls sideways on small screens instead of squashing the columns. */
export function TableWrap({ children, min = 640 }: { children: React.ReactNode; min?: number }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm" style={{ minWidth: min }}>{children}</table>
    </div>
  );
}

export const th = "py-2 pr-3 text-xs font-medium text-muted";
export const td = "py-2.5 pr-3 align-top";
