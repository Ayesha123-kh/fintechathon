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
  const grow = 4; // extra stroke on hover; the radius leaves room so the ring never touches the edge
  const r = (size - thickness - grow) / 2;
  const c = 2 * Math.PI * r;
  const total = segments.reduce((a, s) => a + Math.max(s.value, 0), 0);
  const visible = segments.filter((s) => s.value > 0);
  const gap = visible.length > 1 ? Math.min(4, c * 0.01) : 0;
  let offset = 0;
  const active = segments.find((s) => s.key === hover);
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} role="img" aria-label={label} className="-rotate-90 overflow-visible">
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
                strokeWidth={hover === s.key ? thickness + grow : thickness}
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
  trackClassName = "stroke-chart-track",
  barClassName = "stroke-chart-save",
}: {
  value: number;
  size?: number;
  thickness?: number;
  label: string;
  children?: React.ReactNode;
  trackClassName?: string;
  barClassName?: string;
}) {
  const pct = Math.max(0, Math.min(1, value));
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} role="progressbar"
      aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pct * 100)}>
      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} className="-rotate-90" aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={thickness} className={trackClassName} />
        {pct > 0 && (
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={thickness} strokeLinecap="round"
            strokeDasharray={`${pct * c} ${c}`} className={clsx(barClassName, "transition-[stroke-dasharray] duration-700")} />
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

const CAT_BG = ["bg-cat-1", "bg-cat-2", "bg-cat-3", "bg-cat-4", "bg-cat-5"];

/**
 * One bar split into the month's categories (largest first, five palette colours), then a legend with each
 * category's amount. Categories past the fifth are folded into "Other" so every colour stays distinct.
 */
export function CategoryStack({ rows }: { rows: { category: string; name: string; amount: number | string }[] }) {
  const sorted = rows.map((r) => ({ ...r, value: Number(r.amount) })).filter((r) => r.value > 0).sort((a, b) => b.value - a.value);
  const shown = sorted.length > 5
    ? [...sorted.slice(0, 4), { category: "_other", name: "Other", amount: 0, value: sorted.slice(4).reduce((a, r) => a + r.value, 0) }]
    : sorted;
  const total = shown.reduce((a, r) => a + r.value, 0);
  const [hover, setHover] = useState("");
  if (!total) return null;
  return (
    <div>
      <div className="flex h-4 gap-1" role="img"
        aria-label={shown.map((r) => `${r.name} ${rs(r.value)}`).join(", ")}>
        {shown.map((r, i) => (
          <div key={r.category} title={`${r.name}: ${rs(r.value)} (${Math.round((r.value / total) * 100)}%)`}
            className={clsx("h-full rounded-[3px] transition-opacity first:rounded-l-full last:rounded-r-full", CAT_BG[i],
              hover && hover !== r.category && "opacity-40")}
            style={{ flexGrow: r.value, flexBasis: 0, minWidth: 6 }} />
        ))}
      </div>
      <ul className="mt-6 space-y-3.5">
        {shown.map((r, i) => (
          <li key={r.category} className="flex items-center gap-3 text-[15px] sm:text-base"
            onPointerEnter={() => setHover(r.category)} onPointerLeave={() => setHover("")}>
            <span className={clsx("size-3 shrink-0 rounded-[3px]", CAT_BG[i])} aria-hidden />
            <span className="flex-1 text-ink">{r.name}</span>
            <span className="tabular font-semibold text-ink">{rs(r.value)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
