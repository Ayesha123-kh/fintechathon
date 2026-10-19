"use client";

import clsx from "clsx";
import useSWR from "swr";
import { Card, Spinner } from "@/components/ui";
import { fetcher } from "@/lib/api";
import { PageHeader } from "@/components/admin";

function Overview() {
  const { data } = useSWR<Record<string, number>>("/admin/stats", fetcher, { refreshInterval: 30_000 });
  const { data: audit } = useSWR<{ action: string; target: string; actor: string; at: string }[]>("/admin/audit", fetcher);
  if (!data) return <Spinner />;
  const tiles: [string, string][] = [
    ["users", "Users"], ["active_24h", "Active (24h)"], ["onboarded", "Onboarded"], ["rooms_ready", "Assistants ready"],
    ["rooms_error", "Assistant errors"], ["email_connections", "Email connections"], ["transactions_24h", "Transactions (24h)"],
    ["deals_active", "Active deals"], ["deals_review", "Deals to review"], ["merchants", "Merchants"],
    ["signals_24h", "Signals (24h)"], ["research_24h", "Research notes (24h)"], ["coverage_open", "Coverage requests"],
  ];
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {tiles.map(([k, label]) => (
          <Card key={k} className="p-4">
            <p className="text-xs text-muted">{label}</p>
            <p className={clsx("tabular mt-1 text-2xl font-bold", k === "rooms_error" && data[k] > 0 && "text-danger")}>{data[k] ?? 0}</p>
          </Card>
        ))}
      </div>
      <Card>
        <h2 className="mb-3 font-bold">Recent admin activity</h2>
        {!audit?.length ? <p className="text-sm text-muted">Nothing yet.</p> : (
          <ul className="divide-y divide-line text-sm">
            {audit.slice(0, 15).map((a, i) => (
              <li key={i} className="flex flex-wrap justify-between gap-2 py-2">
                <span><span className="font-semibold">{a.action}</span> <span className="text-muted">{a.target}</span></span>
                <span className="text-xs text-muted">{a.actor} · {new Date(a.at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

export default function Page() {
  return (
    <div className="space-y-5">
      <PageHeader title="Overview" subtitle="Health of the app at a glance." />
      <Overview />
    </div>
  );
}
