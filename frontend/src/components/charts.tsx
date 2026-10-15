"use client";

import clsx from "clsx";
import { useState } from "react";
import { rs } from "@/lib/api";

/** Two-part bar: savings (green) vs. spendable (violet). Validated pair; 2px surface gap between fills. */
export function SplitBar({ savings, expendable, label }: { savings: number; expendable: number; label: string }) {
  const total = Math.max(savings + expendable, 0);
  const s = total ? (savings / total) * 100 : 0;
  const [hover, setHover] = useState<"" | "s" | "e">("");
  return (
    <div className="relative">
      <div className="flex h-3 w-full gap-[2px] overflow-hidden rounded-full bg-chart-track" role="img"
        aria-label={`${label}: savings ${rs(savings)}, spendable ${rs(expendable)}`}>
        {savings > 0 && (
          <div className="h-full rounded-full bg-chart-save" style={{ width: `${s}%` }}
            onPointerEnter={() => setHover("s")} onPointerLeave={() => setHover("")} />
        )}
        {expendable > 0 && (
          <div className="h-full flex-1 rounded-full bg-chart-spend"
            onPointerEnter={() => setHover("e")} onPointerLeave={() => setHover("")} />
        )}
      </div>
      {hover && (
        <div className="pointer-events-none absolute -top-9 left-1/2 z-10 -translate-x-1/2 rounded-xl bg-ink px-3 py-1.5 text-xs whitespace-nowrap text-surface">
          {hover === "s" ? `Savings ${rs(savings)}` : `Spendable ${rs(expendable)}`}
        </div>
      )}
    </div>
  );
}

export function SplitLegend() {
  return (
    <div className="flex gap-4 text-xs text-ink-2">
      <span className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-full bg-chart-save" />Savings</span>
      <span className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-full bg-chart-spend" />Spendable</span>
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
