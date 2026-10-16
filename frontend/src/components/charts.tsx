"use client";

import clsx from "clsx";
import { useState } from "react";
import { rs } from "@/lib/api";

type Segment = { key: string; label: string; value: number; className: string };

/** SVG donut. Segments are separated by a small surface gap; hovering one shows its value in the centre. */
export function Donut({
  segments,
  size = 160,
  thickness = 16,
  center,
  label,
}: {
  segments: Segment[];
  size?: number;
  thickness?: number;
  center?: React.ReactNode;
  label: string;
}) {
  const [hover, setHover] = useState<string>("");
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  const total = segments.reduce((a, s) => a + Math.max(s.value, 0), 0);
  const visible = segments.filter((s) => s.value > 0);
  const gap = visible.length > 1 ? Math.min(4, c * 0.01) : 0;
  let offset = 0;
  const active = segments.find((s) => s.key === hover);
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} role="img" aria-label={label} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={thickness} className="stroke-chart-track" />
        {total > 0 &&
          visible.map((s) => {
            const len = Math.max((s.value / total) * c - gap, 0.001);
            const el = (
              <circle
                key={s.key}
                cx={size / 2}
                cy={size / 2}
                r={r}
                fill="none"
                strokeWidth={hover === s.key ? thickness + 3 : thickness}
                strokeLinecap="butt"
                strokeDasharray={`${len} ${c - len}`}
                strokeDashoffset={-offset}
                className={clsx(s.className, "transition-[stroke-width] duration-150")}
                onPointerEnter={() => setHover(s.key)}
                onPointerLeave={() => setHover("")}
              >
                <title>{`${s.label}: ${rs(s.value)}`}</title>
              </circle>
            );
            offset += len + gap;
            return el;
          })}
      </svg>
      <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
        {active ? (
          <div>
            <p className="text-[11px] text-muted">{active.label}</p>
            <p className="tabular text-sm font-bold">{rs(active.value, { compact: true })}</p>
            <p className="text-[11px] text-muted">{total ? Math.round((active.value / total) * 100) : 0}%</p>
          </div>
        ) : (
          center
        )}
      </div>
    </div>
  );
}

/** Single-value progress ring (goals). */
export function ProgressRing({
  value,
  size = 72,
  thickness = 8,
  label,
  children,
}: {
  value: number;
  size?: number;
  thickness?: number;
  label: string;
  children?: React.ReactNode;
}) {
  const pct = Math.max(0, Math.min(1, value));
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} role="progressbar"
      aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pct * 100)}>
      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} className="-rotate-90" aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={thickness} className="stroke-chart-track" />
        {pct > 0 && (
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={thickness} strokeLinecap="round"
            strokeDasharray={`${pct * c} ${c}`} className="stroke-chart-save transition-[stroke-dasharray] duration-700" />
        )}
      </svg>
      <div className="absolute inset-0 grid place-items-center">
        {children ?? <span className="tabular text-sm font-bold">{Math.round(pct * 100)}%</span>}
      </div>
    </div>
  );
}

/** Savings vs. spendable as one donut; total in the middle. */
export function SplitDonut({ savings, expendable, size = 120, thickness = 14, label }: {
  savings: number; expendable: number; size?: number; thickness?: number; label: string;
}) {
  return (
    <Donut
      size={size}
      thickness={thickness}
      label={`${label}: savings ${rs(savings)}, spendable ${rs(expendable)}`}
      segments={[
        { key: "s", label: "Savings", value: savings, className: "stroke-chart-save" },
        { key: "e", label: "Spendable", value: expendable, className: "stroke-chart-spend" },
      ]}
      center={<p className="tabular text-xs font-bold">{rs(savings + expendable, { compact: true })}</p>}
    />
  );
}

export function SplitLegend() {
  return (
    <div className="flex gap-4 text-xs text-ink-2">
      <span className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-full bg-chart-save" />Savings</span>
      <span className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-full bg-chart-spend ring-1 ring-forest/30" />Spendable</span>
    </div>
  );
}

/** Sorted horizontal bars for one measure (magnitude) in a single hue, with direct value labels. */
export function CategoryBars({ rows }: { rows: { category: string; name: string; amount: number | string }[] }) {
  const max = Math.max(...rows.map((r) => Number(r.amount)), 1);
  const total = rows.reduce((a, r) => a + Number(r.amount), 0);
  const [hover, setHover] = useState<string>("");
  return (
    <ul className="space-y-3">
      {rows.map((r) => {
        const v = Number(r.amount);
        return (
          <li key={r.category} className="relative" onPointerEnter={() => setHover(r.category)} onPointerLeave={() => setHover("")}>
            <div className="mb-1 flex justify-between text-sm">
              <span className="text-ink-2">{r.name}</span>
              <span className="tabular font-semibold">{rs(v)}</span>
            </div>
            <div className="h-2.5 w-full rounded-full bg-chart-track">
              <div className={clsx("h-full rounded-full bg-chart-save transition-[width] duration-700", hover && hover !== r.category && "opacity-50")}
                style={{ width: `${(v / max) * 100}%` }} />
            </div>
            {hover === r.category && (
              <div className="pointer-events-none absolute -top-8 right-0 rounded-xl bg-ink px-3 py-1.5 text-xs text-surface">
                {Math.round((v / total) * 100)}% of this month&apos;s spending
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
